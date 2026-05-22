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
    max_notice_pages: int = 15
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                }
            )

    def _get(self, url: str, params: dict[str, Any] | None = None) -> str:
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        res = self.session.get(url, params=params, timeout=self.timeout)
        res.raise_for_status()
        time.sleep(self.sleep_seconds)
        return res.text

    def find_article_id(self, year: str, semester: str) -> str | None:
        """Find the article ID for the given year and semester based on title patterns."""
        if semester == "1":
            pattern = rf"{year}학년도.*편입생.*오리엔테이션.*안내"
        elif semester == "summer":
            pattern = rf"{year}학년도.*하계.*계절수업.*안내"
        elif semester == "winter":
            pattern = rf"{year}학년도.*동계.*계절수업.*안내"
        else:
            return None

        for page in range(1, self.max_notice_pages + 1):
            params = {"page": page} if page > 1 else None
            html = self._get(NOTICE_LIST_URL, params=params)
            soup = BeautifulSoup(html, "html.parser")
            links = soup.find_all("a", href=re.compile(r"/bbs/mjukr/143/\d+/artclView\.do"))
            for link in links:
                title = " ".join(link.get_text(" ", strip=True).split())
                if re.search(pattern, title):
                    href_value = link.get("href")
                    href = href_value if isinstance(href_value, str) else ""
                    match = re.search(r"/bbs/mjukr/143/(\d+)/artclView\.do", href)
                    if match:
                        return match.group(1)

        return None

    def get_pdf_download_url(self, article_id: str) -> str | None:
        """Find the most relevant PDF download URL from the article view page."""
        url = ARTICLE_VIEW_URL_TEMPLATE.format(article_id=article_id)
        html = self._get(url)
        soup = BeautifulSoup(html, "html.parser")

        candidates: list[tuple[int, str]] = []
        download_links = soup.find_all("a", href=re.compile(r"/bbs/mjukr/143/\d+/download\.do"))

        for link in download_links:
            parent = link.find_parent()
            text = parent.get_text(" ", strip=True) if parent else link.get_text(" ", strip=True)
            normalized_text = " ".join(text.split())
            if ".pdf" not in normalized_text.lower():
                continue

            score = 0
            if any(keyword in normalized_text for keyword in ("시간표", "강의시간표", "개설강좌")):
                score += 100
            if "pdf" in normalized_text.lower():
                score += 10

            href_value = link.get("href")
            href = href_value if isinstance(href_value, str) else ""
            if not href:
                continue
            resolved_href = f"{BASE_URL}{href}" if href.startswith("/") else href
            candidates.append((score, resolved_href))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def download_pdf(self, download_url: str) -> bytes:
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        res = self.session.get(download_url, timeout=self.timeout)
        res.raise_for_status()
        return res.content
