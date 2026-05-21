from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.mju.ac.kr"
NOTICE_LIST_URL = f"{BASE_URL}/mjukr/257/subview.do"
ARTICLE_VIEW_URL_TEMPLATE = f"{BASE_URL}/bbs/mjukr/143/{{article_id}}/artclView.do"

@dataclass(slots=True)
class MyongjiClient:
    timeout: int = 30
    sleep_seconds: float = 0.5
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

    def _get(self, url: str, params: dict[str, Any] | None = None) -> str:
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        res = self.session.get(url, params=params, timeout=self.timeout)
        res.raise_for_status()
        time.sleep(self.sleep_seconds)
        return res.text

    def find_article_id(self, year: str, semester: str) -> str | None:
        """
        Find the article ID for the given year and semester based on title patterns.
        """
        # Patterns based on the task description
        if semester == "1":
            # 2026학년도 편입생 오리엔테이션 안내
            pattern = rf"{year}학년도.*편입생.*오리엔테이션.*안내"
        elif semester == "summer":
            # 2026학년도 하계 계절수업 안내(수강신청 및 등록)
            pattern = rf"{year}학년도.*하계.*계절수업.*안내"
        elif semester == "winter":
            # 2025학년도 동계 계절수업 안내(수강신청 및 등록)
            pattern = rf"{year}학년도.*동계.*계절수업.*안내"
        else:
            return None

        # We might need to iterate through pages if not found on the first page
        # For now, let's try the first page
        html = self._get(NOTICE_LIST_URL)
        soup = BeautifulSoup(html, "html.parser")

        # The list is usually in a table. Looking at the view_text_website output:
        # 1165 [327]2026학년도 하계 계절수업 안내(수강신청 및 등록) ...
        # Links are like /bbs/mjukr/143/231868/artclView.do

        links = soup.find_all("a", href=re.compile(r"/bbs/mjukr/143/\d+/artclView\.do"))
        for link in links:
            title = link.get_text(strip=True)
            if re.search(pattern, title):
                href = link.get("href", "")
                match = re.search(r"/bbs/mjukr/143/(\d+)/artclView\.do", href)
                if match:
                    return match.group(1)

        return None

    def get_pdf_download_url(self, article_id: str) -> str | None:
        """
        Find the PDF download URL from the article view page.
        """
        url = ARTICLE_VIEW_URL_TEMPLATE.format(article_id=article_id)
        html = self._get(url)
        soup = BeautifulSoup(html, "html.parser")

        # Looking for PDF download links.
        # Example from trace: https://www.mju.ac.kr/bbs/mjukr/143/177439/download.do
        # Usually inside a list of attachments.

        # Search for links that look like download links and have .pdf in text or nearby
        download_links = soup.find_all("a", href=re.compile(r"/bbs/mjukr/143/\d+/download\.do"))

        for link in download_links:
            # Check if the filename (text) contains '.pdf'
            parent = link.find_parent()
            text = ""
            if parent:
                text = parent.get_text()
            else:
                text = link.get_text()

            if ".pdf" in text.lower():
                href = link.get("href", "")
                if href.startswith("/"):
                    return f"{BASE_URL}{href}"
                return href

        return None

    def download_pdf(self, download_url: str) -> bytes:
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        res = self.session.get(download_url, timeout=self.timeout)
        res.raise_for_status()
        return res.content
