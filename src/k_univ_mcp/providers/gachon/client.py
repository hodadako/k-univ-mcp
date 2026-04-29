from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://info.gachon.ac.kr"
SHOW_TIMETABLE_PATH = "/ssu/showTimetable.do"
ONLOAD_PATH = "/Ssu1000q/onLoad.do"
DEPT_LIST_PATH = "/Ssu1000q/deptList.do"
MAIN_SEARCH_PATH = "/Ssu1000q/mainSearch.do"
DEFAULT_REFERER = f"{BASE_URL}{SHOW_TIMETABLE_PATH}"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class GachonError(RuntimeError):
    pass


class GachonAuthenticationError(GachonError):
    pass


class GachonTransportError(GachonError):
    pass


class GachonUnexpectedResponseError(GachonError):
    pass


AUTH_SIGNAL_TOKENS = ("login", "session", "expired", "unauthorized", "forbidden", "로그인", "세션", "만료")


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _first_list_value(payload: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    for value in payload.values():
        if isinstance(value, list) and all(isinstance(item, dict) for item in value):
            return value
    return []


@dataclass(slots=True)
class GachonClient:
    cookie_header: str | None = None
    referer: str = DEFAULT_REFERER
    timeout: int = 30
    retry_total: int = 3
    retry_backoff: float = 0.5
    sleep_seconds: float = 0.2
    user_agent: str = DEFAULT_USER_AGENT
    session: requests.Session | None = None
    _bootstrapped: bool = field(init=False, default=False, repr=False)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            retry = Retry(
                total=self.retry_total,
                connect=self.retry_total,
                read=self.retry_total,
                status=self.retry_total,
                allowed_methods=frozenset({"GET", "POST"}),
                status_forcelist=(429, 500, 502, 503, 504),
                backoff_factor=self.retry_backoff,
            )
            adapter = HTTPAdapter(max_retries=retry)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": BASE_URL,
                "Referer": self.referer,
                "User-Agent": self.user_agent,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        if self.cookie_header:
            self._apply_cookie_header(self.cookie_header)

    @staticmethod
    def common_form_prefix() -> dict[str, str]:
        return {
            "@d#": "@d1#",
            "@d1#": "SendData",
            "@d1#tp": "dm",
        }

    def _apply_cookie_header(self, cookie_header: str) -> None:
        session = self.session
        if session is None:
            raise GachonTransportError("Gachon HTTP session is not initialized.")
        session.cookies.clear()
        cookies = _parse_cookie_header(cookie_header)
        if cookies:
            session.cookies.update(cookies)
        self.cookie_header = cookie_header
        self._bootstrapped = True

    def _ensure_wmonid(self) -> None:
        session = self.session
        if session is None:
            raise GachonTransportError("Gachon HTTP session is not initialized.")
        if session.cookies.get("WMONID"):
            self._bootstrapped = True
            return
        response = session.get(f"{BASE_URL}{SHOW_TIMETABLE_PATH}", timeout=self.timeout)
        if response.status_code != 200:
            raise GachonTransportError(f"{SHOW_TIMETABLE_PATH} returned HTTP {response.status_code}.")
        if not session.cookies.get("WMONID"):
            raise GachonAuthenticationError("Gachon bootstrap did not acquire the required WMONID cookie.")
        self._bootstrapped = True

    @staticmethod
    def _contains_auth_signal(value: str) -> bool:
        lowered = value.lower()
        return any(token in lowered for token in AUTH_SIGNAL_TOKENS)

    def _decode_response(self, path: str, response: Response) -> dict[str, Any]:
        text_snippet = response.text[:300]
        if response.status_code in {401, 403}:
            raise GachonAuthenticationError(f"Gachon session rejected {path}. Session may be stale.")
        if response.status_code != 200:
            raise GachonTransportError(f"{path} returned HTTP {response.status_code}: {text_snippet}")
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type or response.text.lstrip().startswith("<"):
            raise GachonAuthenticationError(f"{path} returned HTML instead of JSON. Body={text_snippet}")
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise GachonAuthenticationError(f"{path} returned non-JSON content. Body={text_snippet}") from exc
        if not isinstance(payload, dict):
            raise GachonUnexpectedResponseError(f"{path} returned unexpected payload type: {type(payload).__name__}")
        values = [value for value in payload.values() if isinstance(value, str) and value.strip()]
        if any(self._contains_auth_signal(value) for value in values):
            raise GachonAuthenticationError(f"{path} returned an auth-like payload. Session may be stale.")
        return payload

    def _post(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        self._ensure_wmonid()
        session = self.session
        if session is None:
            raise GachonTransportError("Gachon HTTP session is not initialized.")
        try:
            response = session.post(f"{BASE_URL}{path}", data=data, timeout=self.timeout)
            payload = self._decode_response(path, response)
            time.sleep(self.sleep_seconds)
            return payload
        except requests.RequestException as exc:
            raise GachonTransportError(f"Gachon request failed for {path}: {exc}") from exc

    def load_initial_data(self, group_type: str) -> dict[str, Any]:
        return self._post(ONLOAD_PATH, self.common_form_prefix() | {"@d1#groupType": group_type})

    def list_universities(self, group_type: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        payload = self.load_initial_data(group_type)
        years = _first_list_value(payload, "yearHakgi")
        universities = _first_list_value(payload, "cbUnivCD")
        return years, universities

    def list_faculties(self, year: str, semester: str, group_type: str, univ_code: str) -> list[dict[str, Any]]:
        payload = self._post(
            DEPT_LIST_PATH,
            self.common_form_prefix()
            | {
                "@d1#groupType": group_type,
                "@d1#searchYear": year,
                "@d1#searchTerm": semester,
                "@d1#searchUnivCD": univ_code,
                "@d1#searchDeptCD": "",
                "@d1#searchIsuCD": "001",
                "@d1#searchGrade": "",
                "@d1#searchSubjectNm": "",
            },
        )
        return _first_list_value(payload, "cbDeptCD")

    def list_courses(self, year: str, semester: str, group_type: str, univ_code: str, faculty_code: str) -> list[dict[str, Any]]:
        payload = self._post(
            MAIN_SEARCH_PATH,
            self.common_form_prefix()
            | {
                "@d1#groupType": group_type,
                "@d1#searchYear": year,
                "@d1#searchTerm": semester,
                "@d1#searchUnivCD": univ_code,
                "@d1#searchDeptCD": faculty_code,
                "@d1#searchIsuCD": "001",
                "@d1#searchGrade": "",
                "@d1#searchSubjectNm": "",
            },
        )
        return _first_list_value(payload, "dsMain", "mainList", "cbMain")
