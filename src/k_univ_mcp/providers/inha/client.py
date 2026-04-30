from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://sugang.inha.ac.kr/sugang"
SEARCH_PATH = "/SU_51001/Lec_Time_Search.aspx"
CURRICULUM_PATH = "/SU_51001/curriculum.aspx"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

class InhaClient:
    def __init__(self, timeout: int = 30, sleep_seconds: float = 0.5):
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT
        })

    def _get_initial_form(self, year: str | None = None, semester: str | None = None) -> tuple[dict[str, str], BeautifulSoup]:
        url = f"{BASE_URL}{SEARCH_PATH}"
        params = {}
        if year and semester:
             params = {"year": year, "semester": semester}

        res = self.session.get(url, params=params, timeout=self.timeout)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        form_data = {h.get('name'): h.get('value') or "" for h in soup.find_all('input', type='hidden')}

        for inp in soup.find_all(['input', 'select']):
            name = inp.get('name')
            if name and name not in form_data:
                if inp.name == 'select':
                    opt = inp.find('option', selected=True) or inp.find('option')
                    form_data[name] = opt.get('value') if opt else ""
                elif inp.get('type') != 'submit':
                    form_data[name] = inp.get('value') or ""

        return form_data, soup

    def fetch_departments_from_curriculum(self, year: str | None = None) -> list[dict[str, str]]:
        url = f"{BASE_URL}{CURRICULUM_PATH}"
        # We can try to send year as query param if needed, curriculum.aspx has a year selector
        res = self.session.get(url, timeout=self.timeout)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        table = soup.find('table', id='dgList')
        if not table:
            return []

        depts = []
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) < 3:
                continue

            univ_name = tds[0].text.strip()
            dept_name = tds[1].text.strip()
            major_name = tds[2].text.strip()

            btn = tr.find('input', type='button')
            if btn and btn.get('onclick'):
                # onclick="OpenPrint("0194|002")" -> "0194002"
                match = re.search(r'OpenPrint\("(\d+)\|(\d+)"\)', btn.get('onclick'))
                if match:
                    code = match.group(1) + match.group(2)
                    depts.append({
                        "code": code,
                        "name": f"{dept_name} / {major_name}",
                        "university": univ_name
                    })
        return depts

    def fetch_departments(self) -> list[dict[str, str]]:
        # Fallback to ddlDept if curriculum fails or for simple cases
        _, soup = self._get_initial_form()
        select = soup.find('select', id='ddlDept')
        if not select:
            return []
        return [{"code": opt.get('value'), "name": opt.text.strip()} for opt in select.find_all('option')]

    def fetch_courses(self, faculty_code: str, year: str | None = None, semester: str | None = None) -> list[dict[str, Any]]:
        form_data, soup = self._get_initial_form(year, semester)

        url = f"{BASE_URL}{SEARCH_PATH}"

        # Step 2: Select Dept
        dept_data = form_data.copy()
        dept_data.update({
            "__EVENTTARGET": "ddlDept",
            "ddlDept": faculty_code,
            "hhdSrchGubun": "search"
        })
        res = self.session.post(url, data=dept_data, timeout=self.timeout)
        res.raise_for_status()
        time.sleep(self.sleep_seconds)

        soup = BeautifulSoup(res.text, 'html.parser')
        form_data_v2 = {h.get('name'): h.get('value') or "" for h in soup.find_all('input', type='hidden')}
        for inp in soup.find_all(['input', 'select']):
            name = inp.get('name')
            if name and name not in form_data_v2:
                if inp.name == 'select':
                    opt = inp.find('option', selected=True) or inp.find('option')
                    form_data_v2[name] = opt.get('value') if opt else ""
                elif inp.get('type') != 'submit':
                    form_data_v2[name] = inp.get('value') or ""

        # Step 3: Perform Search
        search_data = form_data_v2.copy()

        search_gubun = search_data.get('hhdSrchGubun', 'search1')
        search_btn = 'ibtnSearch1'
        if search_gubun == 'search2': search_btn = 'ibtnSearch2'
        elif search_gubun == 'search3': search_btn = 'ibtnSearch3'

        search_data[search_btn] = '조회'
        for b in ['ibtnSearch1', 'ibtnSearch2', 'ibtnSearch3']:
            if b != search_btn: search_data.pop(b, None)

        res = self.session.post(url, data=search_data, timeout=self.timeout)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find('table', id='dgList')
        if not table:
            return []

        rows = []
        tr_elements = table.find_all('tr')[1:]
        for tr in tr_elements:
            tds = tr.find_all('td')
            if len(tds) < 10:
                continue
            rows.append({
                "haksu_section": tds[0].text.strip(),
                "title": tds[2].text.strip(),
                "grade": tds[3].text.strip(),
                "credits": tds[4].text.strip(),
                "category": tds[5].text.strip(),
                "time_location": tds[6].text.strip(),
                "professor": tds[7].text.strip(),
                "evaluation": tds[8].text.strip(),
                "note": tds[9].text.strip(),
                "raw_tds": [td.text.strip() for td in tds]
            })

        return rows
