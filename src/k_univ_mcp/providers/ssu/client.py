from __future__ import annotations

import importlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from k_univ_mcp.browser_bootstrap import (
    BrowserBootstrapError,
    BrowserBootstrapSettings,
    BrowserBootstrapTarget,
    ensure_playwright_chromium_installed,
    run_sync_in_playwright_worker,
)

BASE_URL = "https://ecc.ssu.ac.kr/sap/bc/webdynpro/sap/zcmw2100?sap-language=KO"

@dataclass(slots=True)
class SsuClient:
    timeout: int = 30
    browser: str = "headless"
    sleep_seconds: float = 0.5

    def fetch_course_html(self, year: str, semester: str) -> str:
        return run_sync_in_playwright_worker(lambda: self._fetch_course_html_sync(year, semester))

    def _fetch_course_html_sync(self, year: str, semester: str) -> str:
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
                    page.goto(BASE_URL, wait_until="load", timeout=self.timeout * 1000)
                    page.wait_for_timeout(5000)

                    # Click Search to get at least some data (usually current semester)
                    # We can't easily change year/semester without more complex interaction.
                    search_button = page.get_by_role("button", name="검색")
                    if search_button.count() > 0:
                        search_button.click()
                    else:
                        page.click("text=검색")

                    page.wait_for_timeout(5000)

                    return page.content()
                finally:
                    context.close()
                    browser.close()
        except Exception as exc:
            raise RuntimeError(f"SsuClient failed to fetch course HTML: {exc}") from exc
