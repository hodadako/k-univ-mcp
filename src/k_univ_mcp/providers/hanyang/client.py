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

BASE_URL = "https://portal.hanyang.ac.kr"
DEFAULT_REFERER = f"{BASE_URL}/sugang/sulg.do"


class HanyangError(RuntimeError):
    pass


class HanyangAuthenticationError(HanyangError):
    pass


class HanyangTransportError(HanyangError):
    pass


class HanyangUnexpectedResponseError(HanyangError):
    pass


@dataclass(slots=True)
class HanyangClient:
    cookie_header: str = ""
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
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/json+sua; charset=UTF-8",
                "Origin": BASE_URL,
                "Referer": self.referer,
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            }
        )
        if self.cookie_header:
            self._apply_cookie_header(self.cookie_header)

    def _apply_cookie_header(self, cookie_header: str) -> None:
        session = self.session
        if session is None:
            raise HanyangTransportError("Hanyang HTTP session is not initialized.")
        session.cookies.clear()
        # Simple cookie parsing for now
        for cookie in cookie_header.split(";"):
            if "=" in cookie:
                name, value = cookie.strip().split("=", 1)
                session.cookies.set(name, value)
        self.cookie_header = cookie_header

    def _decode_response(self, path: str, response: Response) -> dict[str, Any]:
        if response.status_code in {401, 403}:
            raise HanyangAuthenticationError(f"Hanyang session rejected the request for {path}.")
        if response.status_code != 200:
            raise HanyangTransportError(f"{path} returned HTTP {response.status_code}: {response.text[:300]}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise HanyangUnexpectedResponseError(f"{path} returned non-JSON content: {response.text[:300]}") from exc

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
        params: dict[str, str],
        json_data: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        session = self.session
        if session is None:
            raise HanyangTransportError("Hanyang HTTP session is not initialized.")

        last_error: Exception | None = None
        for attempt in range(self.session_refresh_retries + 1):
            observed_cookie_header = self.cookie_header
            try:
                # Use data=json.dumps to preserve the 'application/json+sua' Content-Type header
                # set in __post_init__. Using json= will override it to 'application/json'.
                response = session.post(url, params=params, data=json.dumps(json_data), timeout=self.timeout)
                payload = self._decode_response(path, response)
                time.sleep(self.sleep_seconds)
                return payload
            except HanyangAuthenticationError as exc:
                last_error = exc
                if not self._refresh_session_if_needed(observed_cookie_header):
                    raise
            except Exception as exc:
                last_error = exc
                if attempt >= self.session_refresh_retries:
                    raise

        if last_error:
            raise last_error
        raise HanyangTransportError(f"Hanyang request failed for {path}")

    def list_programs(self, year: str, semester: str, org_code: str, pgm_id: str, menu_id: str, tk: str) -> dict[str, Any]:
        path = "/sugang/SgscAct/findPgmList.do"
        params = {
            "pgmId": pgm_id,
            "menuId": menu_id,
            "tk": tk,
        }
        json_data = {
            "strJojikGbCd": org_code,
            "strSuupYear": year,
            "strSuupTerm": semester,
        }
        return self._post(path, params, json_data)

    def find_courses(
        self,
        year: str,
        semester: str,
        org_code: str,
        pgm_id: str,
        menu_id: str,
        tk: str,
        max_rows: int = 500,
    ) -> dict[str, Any]:
        path = "/sugang/SgscAct/findSuupSearchSugangSiganpyo.do"
        params = {
            "pgmId": pgm_id,
            "menuId": menu_id,
            "tk": tk,
        }
        json_data = {
            "skipRows": "0",
            "maxRows": str(max_rows),
            "strLocaleGb": "ko",
            "strIsSugangSys": "true",
            "strDetailGb": "0",
            "notAppendQrys": "true",
            "strSuupOprGb": "0",
            "strJojik": org_code,
            "strSuupYear": year,
            "strSuupTerm": semester,
            "strIsuGrade": "",
            "strTsGangjwa": "",
            "strTsGangjwaAll": "0",
            "strTsGangjwa3": "0",
            "strIlbanCommonGb": "",
            "strIsuGbCd": "",
            "strHaksuNo": "",
            "strChgGwamok": "",
            "strGwamok": "",
            "strDaehak": "",
            "strHakgwa": "",
            "strYeongyeok": "",
            "strPgmNm": "",
        }
        return self._post(path, params, json_data)
