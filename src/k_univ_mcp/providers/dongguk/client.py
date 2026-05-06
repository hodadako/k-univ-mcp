from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from k_univ_mcp.providers.dongguk.bootstrap import DonggukSessionState


BASE_URL = "https://support.dongguk.edu"
INDEX_URL = "/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039"
LOGIN_URL = "/main/login/ed/LoginEd40/doLogin.do"
INIT_URL = "/unis/main/view/main/doInit.do"
LOAD_URL = "/ed/edc/lesn/EdcLesn010/doLoad.do"
LIST_URL = "/ed/edc/lesn/EdcLesn010/doList.do"
SEMESTER_URL = "/ed/sys/doListSemCd.do"
DEFAULT_REFERER = f"{BASE_URL}{INDEX_URL}"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

LOGIN_FORM = {
    "_psnIncldPgmResn": "",
    "_psnIncldPgmResnCd": "",
    "_vsRdsnPerm": "",
    "_runningNana": "",
    "_runningMainOpenKey": "[object Object]",
    "_runningLoginIdenNo": "[object Object]",
}

INIT_FORM = {
    "_psnIncldPgmResn": "",
    "_psnIncldPgmResnCd": "",
    "_vsRdsnPerm": "",
    "_runningNana": "",
    "_runningMainOpenKey": "",
    "_runningLoginIdenNo": "",
    "@d1#MAIN_PAGE": "main/singlemain",
    "@d#": "@d1#",
    "@d1#": "dmMainInfo",
    "@d1#tp": "dm",
}

LOAD_FORM = {
    "_psnIncldPgmResn": "",
    "_psnIncldPgmResnCd": "",
    "_vsRdsnPerm": "",
    "_runningNana": "",
    "_runningMainOpenKey": "",
    "_runningLoginIdenNo": "",
    "@d#": "@d1#",
    "@d1#": "dmSearch",
    "@d1#tp": "dm",
}


class DonggukError(RuntimeError):
    pass


class DonggukAuthenticationError(DonggukError):
    pass


class DonggukTransportError(DonggukError):
    pass


class DonggukUnexpectedResponseError(DonggukError):
    pass


AUTH_SIGNAL_TOKENS = (
    "login",
    "logout",
    "session",
    "expired",
    "unauthorized",
    "forbidden",
    "로그인",
    "로그아웃",
    "세션",
    "만료",
)


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _contains_html(value: str) -> bool:
    lowered = value.lower()
    return "<html" in lowered or "<!doctype" in lowered


def _first_list_value(payload: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


@dataclass(slots=True)
class DonggukClient:
    cookie_header: str | None = None
    base_url: str = BASE_URL
    index_path: str = INDEX_URL
    referer: str = DEFAULT_REFERER
    campus_code: str = "CM030.10"
    campus_fg: str = "S"
    orgn_clsf_cd: str = "CM015.110"
    conn_orgn_cd: str = "DS03"
    timeout: int = 30
    retry_total: int = 3
    retry_backoff: float = 0.5
    sleep_seconds: float = 0.2
    session_refresh_retries: int = 1
    user_agent: str = DEFAULT_USER_AGENT
    session: requests.Session | None = None
    refresh_session_state: Callable[[], DonggukSessionState] | None = None
    _session_ready: bool = field(init=False, default=False, repr=False)
    _course_page_payload: dict[str, Any] | None = field(init=False, default=None, repr=False)
    _session_state: DonggukSessionState = field(init=False, repr=False, default_factory=DonggukSessionState.empty)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = self._new_session()
        else:
            self._configure_session(self.session)
        if self.cookie_header:
            self._apply_cookie_header(self.cookie_header)

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        self._configure_session(session)
        return session

    def _configure_session(self, session: requests.Session) -> None:
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
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": self.base_url,
                "Referer": self.referer,
                "User-Agent": self.user_agent,
                "X-Requested-With": "XMLHttpRequest",
            }
        )

    def _apply_cookie_header(self, cookie_header: str) -> None:
        session = self.session
        if session is None:
            raise DonggukTransportError("Dongguk HTTP session is not initialized.")
        session.cookies.clear()
        cookies = _parse_cookie_header(cookie_header)
        if cookies:
            session.cookies.update(cookies)
        self.cookie_header = cookie_header

    def _apply_session_state(self, session_state: DonggukSessionState) -> None:
        self._apply_cookie_header(session_state.cookie_header)
        self._session_state = session_state

    @staticmethod
    def _contains_auth_signal(value: str) -> bool:
        lowered = value.lower()
        return any(token in lowered for token in AUTH_SIGNAL_TOKENS)

    @classmethod
    def _raise_for_auth_like_payload(cls, path: str, payload: dict[str, Any]) -> None:
        error_info = payload.get("ERRMSGINFO")
        if not isinstance(error_info, dict):
            return
        status_code = error_info.get("STATUSCODE")
        messages = [value for value in error_info.values() if isinstance(value, str) and value.strip()]
        if status_code not in {None, 0, "0"} or any(cls._contains_auth_signal(value) for value in messages):
            details = messages[0] if messages else f"status={status_code}"
            raise DonggukAuthenticationError(f"{path} returned an auth-like error payload. {details}")

    def _reset_session(self) -> None:
        self.session = self._new_session()
        if self.cookie_header:
            self._apply_cookie_header(self.cookie_header)
        self._session_ready = False
        self._course_page_payload = None

    def _running_fields(self) -> dict[str, str]:
        return {
            "_runningNana": self._session_state.running_nana,
            "_runningMainOpenKey": self._session_state.running_main_open_key,
            "_runningLoginIdenNo": self._session_state.running_login_iden_no,
        }

    def _merge_runtime_fields(self, data: dict[str, str]) -> dict[str, str]:
        merged = dict(data)
        merged.update(self._running_fields())
        return merged

    def _refresh_session_state_if_needed(self) -> bool:
        if self.refresh_session_state is None or self.session_refresh_retries <= 0:
            return False
        refreshed_state = self.refresh_session_state()
        self._apply_session_state(refreshed_state)
        self._session_ready = False
        self._course_page_payload = None
        return True

    def _request(self, method: str, path: str, *, data: dict[str, str] | None = None) -> Response:
        session = self.session
        if session is None:
            raise DonggukTransportError("Dongguk HTTP session is not initialized.")
        url = f"{self.base_url}{path}"
        try:
            response = session.request(method, url, data=data, timeout=self.timeout)
        except requests.RequestException as exc:
            raise DonggukTransportError(f"Dongguk request failed for {path}: {exc}") from exc
        time.sleep(self.sleep_seconds)
        return response

    def _decode_response(self, path: str, response: Response) -> dict[str, Any]:
        text_snippet = response.text[:400]
        if response.status_code in {401, 403}:
            raise DonggukAuthenticationError(f"Dongguk session rejected {path}. Session may be stale.")
        if response.status_code != 200:
            raise DonggukTransportError(f"{path} returned HTTP {response.status_code}: {text_snippet}")
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type or _contains_html(response.text):
            raise DonggukAuthenticationError(f"{path} returned HTML instead of JSON. Body={text_snippet}")
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise DonggukAuthenticationError(f"{path} returned non-JSON content. Body={text_snippet}") from exc
        if not isinstance(payload, dict):
            raise DonggukUnexpectedResponseError(f"{path} returned unexpected payload type: {type(payload).__name__}")
        self._raise_for_auth_like_payload(path, payload)
        return payload

    def _bootstrap_once(self) -> dict[str, Any]:
        if self.refresh_session_state is not None:
            self._apply_session_state(self.refresh_session_state())
            payload = self._decode_response(LOAD_URL, self._request("POST", LOAD_URL, data=self._merge_runtime_fields(LOAD_FORM)))
            self._session_ready = True
            self._course_page_payload = payload
            return payload
        self._request("GET", self.index_path)
        self._decode_response(LOGIN_URL, self._request("POST", LOGIN_URL, data=LOGIN_FORM))
        self._decode_response(INIT_URL, self._request("POST", INIT_URL, data=INIT_FORM))
        payload = self._decode_response(LOAD_URL, self._request("POST", LOAD_URL, data=self._merge_runtime_fields(LOAD_FORM)))
        self._session_ready = True
        self._course_page_payload = payload
        return payload

    def ensure_session(self, *, force: bool = False) -> dict[str, Any]:
        if self._session_ready and not force and self._course_page_payload is not None:
            return self._course_page_payload

        last_error: Exception | None = None
        attempts = self.session_refresh_retries + 1
        for attempt in range(attempts):
            if self.refresh_session_state is None:
                self._reset_session()
            try:
                return self._bootstrap_once()
            except (DonggukAuthenticationError, DonggukUnexpectedResponseError, DonggukTransportError) as exc:
                last_error = exc
                if attempt >= self.session_refresh_retries:
                    raise
        if last_error is not None:
            raise last_error
        raise DonggukTransportError("Dongguk session bootstrap failed without a response payload.")

    def load_course_page(self) -> dict[str, Any]:
        if self._session_ready and self._course_page_payload is not None:
            return self._course_page_payload
        return self.ensure_session()

    def fetch_semesters(self) -> list[dict[str, Any]]:
        self.ensure_session()
        payload = self._post_json(SEMESTER_URL, {"ORGN_CLSF_CD": self.orgn_clsf_cd})
        rows = _first_list_value(payload, "__dsCodeSemCd", "dsCodeSemCd")
        semesters: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            code = row.get("OPEN_SEM_CD") or row.get("SEM_CD")
            if not code:
                continue
            code_text = str(code)
            if code_text in seen:
                continue
            seen.add(code_text)
            semesters.append(row)
        return semesters

    def _post_json(self, path: str, data: dict[str, str]) -> dict[str, Any]:
        if (not self.cookie_header or not all(self._running_fields().values())) and self.refresh_session_state is not None:
            self._refresh_session_state_if_needed()
        last_error: Exception | None = None
        for attempt in range(self.session_refresh_retries + 1):
            try:
                payload = self._decode_response(path, self._request("POST", path, data=self._merge_runtime_fields(data)))
                return payload
            except (DonggukAuthenticationError, DonggukUnexpectedResponseError, DonggukTransportError) as exc:
                last_error = exc
                if attempt >= self.session_refresh_retries:
                    raise
                if self.refresh_session_state is not None:
                    self._refresh_session_state_if_needed()
                else:
                    self._reset_session()
                    self._bootstrap_once()
        if last_error is not None:
            raise last_error
        raise DonggukTransportError(f"Dongguk request failed for {path} without a response payload.")

    @staticmethod
    def _collect_rows(value: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if isinstance(value, dict):
            rows.append(value)
            for nested in value.values():
                rows.extend(DonggukClient._collect_rows(nested))
        elif isinstance(value, list):
            for item in value:
                rows.extend(DonggukClient._collect_rows(item))
        return rows

    def list_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str) -> list[dict[str, Any]]:
        self.ensure_session()
        form = {
            "_psnIncldPgmResn": "",
            "_psnIncldPgmResnCd": "",
            "_vsRdsnPerm": "",
            "_runningNana": self._session_state.running_nana,
            "_runningMainOpenKey": self._session_state.running_main_open_key,
            "_runningLoginIdenNo": self._session_state.running_login_iden_no,
            "@d1#OPEN_ORGN_CLSF_CD": self.orgn_clsf_cd,
            "@d1#OPEN_YY": year,
            "@d1#OPEN_SEM_CD": semester,
            "@d1#SBJ_NO": "",
            "@d1#COLG_CD": college_code,
            "@d1#DPT_CD": department_code,
            "@d1#MJR_CD": "",
            "@d1#CURI_CD": "",
            "@d1#DETL_CURI_CD": "",
            "@d1#EMP_NO": "",
            "@d1#CAMP_FG": self.campus_fg,
            "@d1#ORGN_LCLSF_CD": "",
            "@d1#LESN_REGN_CD": "",
            "@d1#LESN_STY_CD": "",
            "@d1#DAY_CD": "",
            "@d1#LOCALE": "ko",
            "@d1#CONN_ORGN_CD": self.conn_orgn_cd,
            "@d#": "@d1#",
            "@d1#": "dmSearch",
            "@d1#tp": "dm",
        }

        payload = self._post_json(LIST_URL, form)
        courses = _first_list_value(payload, "dsMain")
        if courses:
            return courses

        for value in payload.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []
