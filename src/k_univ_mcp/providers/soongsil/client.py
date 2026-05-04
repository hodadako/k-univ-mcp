from __future__ import annotations

import importlib
from dataclasses import dataclass
import re
from typing import Any, Callable

from k_univ_mcp.browser_bootstrap import (
    BrowserBootstrapError,
    ensure_playwright_chromium_installed,
    run_sync_in_playwright_worker,
)
from k_univ_mcp.providers.soongsil.models import SoongsilCatalogEntry

BASE_URL = "https://ecc.ssu.ac.kr/sap/bc/webdynpro/sap/zcmw2100?sap-language=KO"
NO_DATA_TEXT = "해당 테이블에 데이터가 없습니다."
COURSE_TABLE_SELECTOR = "#WD0184"

@dataclass(slots=True)
class SoongsilClient:
    timeout: int = 30
    browser: str = "headless"
    sleep_seconds: float = 0.5

    def list_catalog(self, year: str, semester: str) -> list[SoongsilCatalogEntry]:
        return run_sync_in_playwright_worker(lambda: self._list_catalog_sync(year, semester))

    def collect_course_pages(
        self,
        year: str,
        semester: str,
        entries: list[SoongsilCatalogEntry],
    ) -> list[tuple[SoongsilCatalogEntry, str]]:
        return run_sync_in_playwright_worker(lambda: self._collect_course_pages_sync(year, semester, entries))

    def _list_catalog_sync(self, year: str, semester: str) -> list[SoongsilCatalogEntry]:
        return self._run_with_page(lambda page: self._extract_catalog(page, year, semester))

    def _collect_course_pages_sync(
        self,
        year: str,
        semester: str,
        entries: list[SoongsilCatalogEntry],
    ) -> list[tuple[SoongsilCatalogEntry, str]]:
        return self._run_with_page(lambda page: self._collect_pages(page, year, semester, entries))

    def _run_with_page(self, callback: Callable[[Any], Any]) -> Any:
        try:
            playwright_sync_api = importlib.import_module("playwright.sync_api")
        except ImportError as exc:
            raise BrowserBootstrapError(
                "Playwright is not installed. Install project dependencies and run 'playwright install chromium'."
            ) from exc

        playwright_error = getattr(playwright_sync_api, "Error")
        sync_playwright = getattr(playwright_sync_api, "sync_playwright")

        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=self.browser == "headless")
                except playwright_error:
                    ensure_playwright_chromium_installed()
                    browser = playwright.chromium.launch(headless=self.browser == "headless")

                context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                page = context.new_page()

                try:
                    return callback(page)
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            raise RuntimeError(f"SoongsilClient failed to fetch course HTML: {exc}") from exc

    def _extract_catalog(self, page: Any, year: str, semester: str) -> list[SoongsilCatalogEntry]:
        self._open_course_page(page, year, semester)
        entries: list[SoongsilCatalogEntry] = []
        seen: set[tuple[str, str]] = set()

        for college_name in self._list_filter_options(page, 0):
            self._select_filter_option(page, 0, college_name)
            college_code, selected_college_name = self._selected_filter_value(page, 0)
            for department_name in self._list_filter_options(page, 1):
                self._select_filter_option(page, 1, department_name)
                department_code, selected_department_name = self._selected_filter_value(page, 1)
                key = (college_code, department_code)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    SoongsilCatalogEntry(
                        college_code=college_code,
                        college_name=selected_college_name,
                        department_code=department_code,
                        department_name=selected_department_name,
                    )
                )

        return entries

    def _collect_pages(
        self,
        page: Any,
        year: str,
        semester: str,
        entries: list[SoongsilCatalogEntry],
    ) -> list[tuple[SoongsilCatalogEntry, str]]:
        self._open_course_page(page, year, semester)
        collected: list[tuple[SoongsilCatalogEntry, str]] = []

        for entry in entries:
            self._select_filter_option(page, 0, entry.college_name)
            self._select_filter_option(page, 1, entry.department_name)
            self._click_search(page)
            collected.append((entry, page.content()))

        return collected

    def _open_course_page(self, page: Any, year: str, semester: str) -> None:
        page.goto(BASE_URL, wait_until="load", timeout=self.timeout * 1000)
        page.wait_for_timeout(3000)
        self._select_global_option(page, "학년도", f"{year}학년도")
        self._select_global_option(page, "학기", self._normalize_semester_label(semester))

    def _normalize_semester_label(self, semester: str) -> str:
        semester_text = semester.strip()
        mapping = {
            "1": "1학기",
            "2": "2학기",
            "여름": "여름학기",
            "여름학기": "여름학기",
            "1학기": "1학기",
            "2학기": "2학기",
        }
        return mapping.get(semester_text, semester_text)

    def _select_global_option(self, page: Any, label: str, option_text: str) -> None:
        listbox = page.get_by_role("listbox", name=label)
        current = listbox.evaluate("(element) => element.value || element.textContent || ''").strip()
        if current == option_text:
            return
        listbox.click()
        page.wait_for_timeout(300)
        page.get_by_role("option", name=option_text, exact=True).click()
        page.wait_for_timeout(700)

    def _filter_input_ids(self, page: Any) -> list[str]:
        ids = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('#WDF5-cnt [role=listbox]'))
                .map((element) => element.id)
                .filter(Boolean)
            """
        )
        return ids[:3]

    def _list_filter_options(self, page: Any, index: int) -> list[str]:
        input_id = self._filter_input_ids(page)[index]
        page.locator(f"#{input_id}-btn").click()
        page.wait_for_timeout(500)
        options = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('[role=option]'))
                .map((element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                        text: (element.textContent || '').trim(),
                        width: rect.width,
                        height: rect.height,
                    };
                })
                .filter((entry) => entry.text && entry.width > 0 && entry.height > 0)
                .map((entry) => entry.text)
            """
        )
        page.locator(f"#{input_id}-btn").click()
        page.wait_for_timeout(200)
        return options

    def _select_filter_option(self, page: Any, index: int, option_text: str) -> None:
        input_id = self._filter_input_ids(page)[index]
        current = page.locator(f"#{input_id}").evaluate("(element) => element.value || ''").strip()
        if current == option_text:
            return
        page.locator(f"#{input_id}-btn").click()
        page.wait_for_timeout(300)
        page.get_by_role("option", name=option_text, exact=True).click()
        page.wait_for_timeout(800)

    def _selected_filter_value(self, page: Any, index: int) -> tuple[str, str]:
        input_id = self._filter_input_ids(page)[index]
        value = page.locator(f"#{input_id}").evaluate("(element) => element.value || ''").strip()
        lsdata = page.locator(f"#{input_id}").get_attribute("lsdata") or ""
        match = re.search(r"4:'([^']+)'(?:,5:'([^']+)')?", lsdata)
        code = match.group(1) if match else value
        name = match.group(2) if match and match.group(2) else value
        name = re.sub(r"\\x([0-9A-Fa-f]{2})", lambda matched: chr(int(matched.group(1), 16)), name)
        return code, name

    def _click_search(self, page: Any) -> None:
        previous_text = page.locator(COURSE_TABLE_SELECTOR).text_content() or ""
        page.locator("#WDF5-cnt").get_by_role("button", name="검색").click()
        page.wait_for_timeout(2500)
        current_text = page.locator(COURSE_TABLE_SELECTOR).text_content() or ""
        if current_text == previous_text:
            page.wait_for_timeout(2500)
