from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://sugang.sungshin.ac.kr"
ONLOAD_PATH = "/findBCRM02010OnLoad.do"
SEARCH_PATH = "/findBCRM02010Main.do"

@dataclass(slots=True)
class SungshinClient:
    timeout: int = 30
    retry_total: int = 3
    retry_backoff: float = 0.5
    sleep_seconds: float = 0.2
    session: requests.Session | None = None

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
                "Referer": f"{BASE_URL}/findBCRM02010.do",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            }
        )

    def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        if self.session is None:
             raise RuntimeError("Session is not initialized")

        try:
            response = self.session.post(url, data=data, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            time.sleep(self.sleep_seconds)
            return payload
        except requests.RequestException as exc:
            raise RuntimeError(f"Sungshin request failed for {path}: {exc}") from exc

    def onload(self) -> dict[str, Any]:
        return self._post(ONLOAD_PATH)

    def search_courses(
        self,
        year: str,
        semester: str,
        org_clsf_code: str = "",
        sbj_mng_code: str = "",
        obj_crs_code: str = "",
        dpt_mjr_code: str = "",
        sbj_no_nm: str = "",
        cpdiv_code: str = "",
        cmp_code: str = "",
        sbj_area_code: str = "",
        char_sbj_area_code: str = "",
    ) -> list[dict[str, Any]]:
        data = {
            "yy": year,
            "semCd": semester,
            "orgClsfCd": org_clsf_code,
            "sbjMngCd": sbj_mng_code,
            "objCrsCd": obj_crs_code,
            "dptMjrCd": dpt_mjr_code,
            "sbjNoNm": sbj_no_nm,
            "cpdivCd": cpdiv_code,
            "cmpCd": cmp_code,
            "sbjAreaCd": sbj_area_code,
            "charSbjAreaCd": char_sbj_area_code,
        }
        return self._post(SEARCH_PATH, data=data)
