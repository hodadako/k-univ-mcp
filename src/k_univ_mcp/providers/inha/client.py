from __future__ import annotations

import re
import time
from typing import Any, cast

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://sugang.inha.ac.kr/sugang"
SEARCH_PATH = "/SU_51001/Lec_Time_Search.aspx"
CURRICULUM_PATH = "/SU_51001/curriculum.aspx"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class InhaClient:
    timeout: int
    sleep_seconds: float
    session: requests.Session

    def __init__(self, timeout: int = 30, sleep_seconds: float = 0.5):
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT
        })

    def _get_initial_form(self, year: str | None = None, semester: str | None = None) -> tuple[dict[str, str], BeautifulSoup]:
        url = f"{BASE_URL}{SEARCH_PATH}"
        params: dict[str, str] = {}
        if year and semester:
            params = {"year": year, "semester": semester}

        res = self.session.get(url, params=params, timeout=self.timeout)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        form_data: dict[str, str] = {}
        for h in soup.find_all("input", type="hidden"):
            name = h.get("name")
            if isinstance(name, str):
                form_data[name] = str(h.get("value") or "")

        for inp in soup.find_all(["input", "select"]):
            name = inp.get("name")
            if not isinstance(name, str) or name in form_data:
                continue

            if inp.name == "select":
                opt = inp.find("option", selected=True) or inp.find("option")
                if isinstance(opt, Tag):
                    form_data[name] = str(opt.get("value") or "")
            elif inp.get("type") != "submit":
                form_data[name] = str(inp.get("value") or "")

        return form_data, soup

    def fetch_departments_from_curriculum(self, year: str | None = None) -> list[dict[str, str]]:
        _ = year  # placeholder if needed later
        url = f"{BASE_URL}{CURRICULUM_PATH}"
        res = self.session.get(url, timeout=self.timeout)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        table = soup.find("table", id="dgList")
        if not isinstance(table, Tag):
            return []

        depts: list[dict[str, str]] = []
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            univ_name = tds[0].get_text(strip=True)
            dept_name = tds[1].get_text(strip=True)
            major_name = tds[2].get_text(strip=True)

            btn = tr.find("input", type="button")
            if isinstance(btn, Tag):
                onclick = btn.get("onclick")
                if isinstance(onclick, str):
                    match = re.search(r'OpenPrint\("(\d+)\|(\d+)"\)', onclick)
                    if match:
                        code = match.group(1) + match.group(2)
                        depts.append({
                            "code": code,
                            "name": f"{dept_name} / {major_name}",
                            "university": univ_name
                        })
        return depts

    def fetch_departments(self) -> list[dict[str, str]]:
        _, soup = self._get_initial_form()
        select = soup.find("select", id="ddlDept")
        if not isinstance(select, Tag):
            return []

        results: list[dict[str, str]] = []
        for opt in select.find_all("option"):
            val = opt.get("value")
            if isinstance(val, str):
                results.append({"code": val, "name": opt.get_text(strip=True)})
        return results

    def fetch_courses(self, faculty_code: str, year: str | None = None, semester: str | None = None) -> list[dict[str, Any]]:
        form_data, _ = self._get_initial_form(year, semester)

        url = f"{BASE_URL}{SEARCH_PATH}"

        dept_data = form_data.copy()
        dept_data.update({
            "__EVENTTARGET": "ddlDept",
            "ddlDept": faculty_code,
            "hhdSrchGubun": "search"
        })
        res = self.session.post(url, data=dept_data, timeout=self.timeout)
        res.raise_for_status()
        time.sleep(self.sleep_seconds)

        soup = BeautifulSoup(res.text, "html.parser")
        form_data_v2: dict[str, str] = {}
        for h in soup.find_all("input", type="hidden"):
            name = h.get("name")
            if isinstance(name, str):
                form_data_v2[name] = str(h.get("value") or "")

        for inp in soup.find_all(["input", "select"]):
            name = inp.get("name")
            if not isinstance(name, str) or name in form_data_v2:
                continue
            if inp.name == "select":
                opt = inp.find("option", selected=True) or inp.find("option")
                if isinstance(opt, Tag):
                    form_data_v2[name] = str(opt.get("value") or "")
            elif inp.get("type") != "submit":
                form_data_v2[name] = str(inp.get("value") or "")

        search_data = form_data_v2.copy()
        search_gubun = search_data.get("hhdSrchGubun", "search1")
        search_btn = "ibtnSearch1"
        if search_gubun == "search2":
            search_btn = "ibtnSearch2"
        elif search_gubun == "search3":
            search_btn = "ibtnSearch3"

        search_data[search_btn] = "조회"
        _ = search_data.pop("ibtnSearch1", None) if search_btn != "ibtnSearch1" else None
        _ = search_data.pop("ibtnSearch2", None) if search_btn != "ibtnSearch2" else None
        _ = search_data.pop("ibtnSearch3", None) if search_btn != "ibtnSearch3" else None

        res = self.session.post(url, data=search_data, timeout=self.timeout)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table", id="dgList")
        if not isinstance(table, Tag):
            return []

        rows: list[dict[str, Any]] = []
        tr_elements = table.find_all("tr")[1:]
        for tr in tr_elements:
            tds = tr.find_all("td")
            if len(tds) < 10:
                continue
            rows.append({
                "haksu_section": tds[0].get_text(strip=True),
                "title": tds[2].get_text(strip=True),
                "grade": tds[3].get_text(strip=True),
                "credits": tds[4].get_text(strip=True),
                "category": tds[5].get_text(strip=True),
                "time_location": tds[6].get_text(strip=True),
                "professor": tds[7].get_text(strip=True),
                "evaluation": tds[8].get_text(strip=True),
                "note": tds[9].get_text(strip=True),
                "raw_tds": [td.get_text(strip=True) for td in tds]
            })

        return rows
