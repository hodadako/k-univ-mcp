from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from k_univ_mcp.providers.yonsei.bootstrap import parse_cookie_header

BASE_URL = "https://underwood1.yonsei.ac.kr"
DEFAULT_REFERER = f"{BASE_URL}/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko"
FACULTIES_PATH = "/sch/sles/SlescsCtr/findSchSlesHandbList.do"
COURSES_PATH = "/sch/sles/SlessyCtr/findAtnlcHandbList.do"


class YonseiError(RuntimeError):
    pass


class YonseiAuthenticationError(YonseiError):
    pass


class YonseiTransportError(YonseiError):
    pass


class YonseiUnexpectedResponseError(YonseiError):
    pass


AUTH_SIGNAL_TOKENS = (
    "login",
    "session",
    "expired",
    "unauthorized",
    "forbidden",
    "denied",
    "netfunnel",
    "block",
    "redirect",
    "로그인",
    "세션",
    "만료",
    "차단",
)

AUTH_SIGNAL_KEYS = (
    "message",
    "msg",
    "error",
    "errmsg",
    "errormessage",
    "resultmsg",
    "redirecturl",
    "location",
    "exception",
    "alert",
)


@dataclass(slots=True)
class YonseiClient:
    cookie_header: str
    referer: str = DEFAULT_REFERER
    timeout: int = 30
    retry_total: int = 3
    retry_backoff: float = 0.5
    sleep_seconds: float = 0.2
    session_refresh_retries: int = 1
    refresh_cookie_header: Callable[[], str] | None = None
    session: requests.Session | None = None
    _refresh_lock: threading.Lock = field(init=False, repr=False, default_factory=threading.Lock)

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
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        self._apply_cookie_header(self.cookie_header)

    @staticmethod
    def common_form_prefix() -> dict[str, str]:
        return {
            "_menuId": "MTA5MzM2MTI3MjkzMTI2NzYwMDA=",
            "_menuNm": "",
            "_pgmId": "NDE0MDA4NTU1NjY=",
            "@d#": "@d1#",
            "@d1#": "dmCond",
            "@d1#tp": "dm",
        }

    @classmethod
    def discovery_form(
        cls,
        *,
        dataset_name: str,
        year: str,
        semester: str,
        level: str = "B",
        lv1: str = "%",
        lv2: str = "%",
        lv3: str = "%",
        sysinst_div_code: str = "%",
        univ_gbn: str = "A",
        find_auth_gbn: str = "8",
    ) -> dict[str, str]:
        return cls.common_form_prefix() | {
            "@d1#dsNm": dataset_name,
            "@d1#level": level,
            "@d1#lv1": lv1,
            "@d1#lv2": lv2,
            "@d1#lv3": lv3,
            "@d1#sysinstDivCd": sysinst_div_code,
            "@d1#univGbn": univ_gbn,
            "@d1#findAuthGbn": find_auth_gbn,
            "@d1#syy": year,
            "@d1#smtDivCd": semester,
        }

    def _apply_cookie_header(self, cookie_header: str) -> None:
        session = self.session
        if session is None:
            raise YonseiTransportError("Yonsei HTTP session is not initialized.")
        session.cookies.clear()
        cookies = parse_cookie_header(cookie_header)
        if cookies:
            session.cookies.update(cookies)
        self.cookie_header = cookie_header

    @staticmethod
    def _contains_auth_signal(value: str) -> bool:
        lowered = value.lower()
        return any(token in lowered for token in AUTH_SIGNAL_TOKENS)

    @classmethod
    def _auth_signal_values(cls, payload: dict[str, Any]) -> list[str]:
        values: list[str] = []
        for key, value in payload.items():
            lowered_key = key.lower()
            if not any(token in lowered_key for token in AUTH_SIGNAL_KEYS):
                continue
            if isinstance(value, str) and value.strip():
                values.append(value)
            elif isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if (
                        isinstance(nested_value, str)
                        and nested_value.strip()
                        and any(token in nested_key.lower() for token in AUTH_SIGNAL_KEYS)
                    ):
                        values.append(nested_value)
        return values

    @classmethod
    def _raise_for_auth_like_payload(cls, path: str, payload: dict[str, Any]) -> None:
        values = cls._auth_signal_values(payload)
        if any(cls._contains_auth_signal(value) for value in values):
            raise YonseiAuthenticationError(
                f"{path} returned an auth-like error payload. Session may be expired or blocked by NetFunnel."
            )

    @staticmethod
    def _is_suspicious_empty_faculty_payload(payload: dict[str, Any]) -> bool:
        raw_faculties = payload.get("dsFaclyCd")
        if raw_faculties != []:
            return False
        other_non_empty_lists = [value for key, value in payload.items() if key != "dsFaclyCd" and isinstance(value, list) and value]
        if other_non_empty_lists:
            return False
        if any(isinstance(value, str) and value.strip() for value in payload.values()):
            return False
        return len(payload) <= 2

    def _decode_response(self, path: str, response: Response) -> dict[str, Any]:
        text_snippet = response.text[:300]
        if response.status_code in {401, 403}:
            raise YonseiAuthenticationError(
                f"Yonsei session rejected the request for {path}. Check JSESSIONID / NetFunnel_ID cookie freshness."
            )
        if response.status_code != 200:
            raise YonseiTransportError(f"{path} returned HTTP {response.status_code}: {text_snippet}")

        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type or response.text.lstrip().startswith("<"):
            raise YonseiAuthenticationError(
                f"{path} returned HTML instead of JSON. Session may be expired or blocked by NetFunnel. Body={text_snippet}"
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise YonseiAuthenticationError(
                f"{path} returned non-JSON content. Session may be expired or blocked by NetFunnel. Body={text_snippet}"
            ) from exc

        if not isinstance(payload, dict):
            raise YonseiUnexpectedResponseError(f"{path} returned unexpected payload type: {type(payload).__name__}")
        self._raise_for_auth_like_payload(path, payload)
        return payload

    def _refresh_session_if_needed(self, stale_cookie_header: str) -> bool:
        if self.refresh_cookie_header is None or self.session_refresh_retries <= 0:
            return False

        with self._refresh_lock:
            if self.cookie_header != stale_cookie_header:
                return True
            refreshed_cookie_header = self.refresh_cookie_header()
            self._apply_cookie_header(refreshed_cookie_header)
            return True

    def _post(
        self,
        path: str,
        data: dict[str, Any],
        *,
        payload_validator: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        session = self.session
        if session is None:
            raise YonseiTransportError("Yonsei HTTP session is not initialized.")

        if not self.cookie_header and self.refresh_cookie_header is not None:
            self._refresh_session_if_needed("")

        last_auth_error: YonseiAuthenticationError | None = None
        for attempt in range(self.session_refresh_retries + 1):
            observed_cookie_header = self.cookie_header
            try:
                response = session.post(url, data=data, timeout=self.timeout)
                payload = self._decode_response(path, response)
                if payload_validator is not None:
                    payload_validator(payload)
                time.sleep(self.sleep_seconds)
                return payload
            except requests.RequestException as exc:
                raise YonseiTransportError(f"Yonsei request failed for {path}: {exc}") from exc
            except YonseiAuthenticationError as exc:
                last_auth_error = exc
                if attempt >= self.session_refresh_retries or not self._refresh_session_if_needed(observed_cookie_header):
                    raise

        if last_auth_error is not None:
            raise last_auth_error
        raise YonseiTransportError(f"Yonsei request failed for {path} without a response payload.")

    def _validate_faculties_payload(self, payload: dict[str, Any]) -> None:
        raw_faculties = payload.get("dsFaclyCd", [])
        if not isinstance(raw_faculties, list):
            raise YonseiUnexpectedResponseError("Yonsei faculty response did not include a list in dsFaclyCd.")
        if self._is_suspicious_empty_faculty_payload(payload):
            raise YonseiAuthenticationError(
                "Yonsei faculty response returned an abnormal empty payload. Session may be expired or blocked by NetFunnel."
            )

    @staticmethod
    def _extract_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = payload.get(key, [])
        if not isinstance(value, list):
            raise YonseiUnexpectedResponseError(f"Yonsei response did not include a list in {key}.")
        return value

    def list_campuses(self, year: str, semester: str) -> list[dict[str, Any]]:
        payload = self._post(
            FACULTIES_PATH,
            self.discovery_form(dataset_name="dsCampsBusnsCd", year=year, semester=semester),
        )
        return self._extract_list(payload, "dsCampsBusnsCd")

    def list_universities(self, year: str, semester: str, campus_code: str) -> list[dict[str, Any]]:
        payload = self._post(
            FACULTIES_PATH,
            self.discovery_form(dataset_name="dsUnivCd", year=year, semester=semester, lv1=campus_code),
        )
        return self._extract_list(payload, "dsUnivCd")

    def list_faculties(self, year: str, semester: str, campus_code: str, univ_code: str) -> list[dict[str, Any]]:
        payload = self._post(
            FACULTIES_PATH,
            self.common_form_prefix()
            | {
                "@d1#syy": year,
                "@d1#smtDivCd": semester,
                "@d1#campsBusnsCd": campus_code,
                "@d1#univCd": univ_code,
            },
            payload_validator=self._validate_faculties_payload,
        )
        return self._extract_list(payload, "dsFaclyCd")

    def list_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        payload = self._post(
            COURSES_PATH,
            self.common_form_prefix()
            | {
                "@d1#syy": year,
                "@d1#smtDivCd": semester,
                "@d1#campsBusnsCd": campus_code,
                "@d1#univCd": univ_code,
                "@d1#faclyCd": faculty_code,
                "@d1#hy": "",
                "@d1#cdt": "%",
                "@d1#kwdDivCd": "1",
                "@d1#searchGbn": "1",
                "@d1#kwd": "",
                "@d1#allKwd": "",
                "@d1#engChg": "",
                "@d1#prnGbn": "false",
                "@d1#lang": "",
                "@d1#campsDivCd": "",
                "@d1#stuno": "",
            },
        )

        for key in ("dsSlessyList", "dsMain", "dsAtnlcHandbList"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

        for value in payload.values():
            if isinstance(value, list):
                return value
        return []
