from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from k_univ_mcp.browser_bootstrap import (
    BrowserBootstrapError,
    BrowserBootstrapSettings,
    BrowserBootstrapTarget,
    ensure_playwright_chromium_installed,
    run_sync_in_playwright_worker,
    serialize_cookie_header,
)

LOAD_PATH_SUFFIX = "/ed/edc/lesn/EdcLesn010/doLoad.do"
DONGGUK_REQUIRED_BROWSER_COOKIES = ("JSESSIONID",)


@dataclass(slots=True, frozen=True)
class DonggukSessionState:
    cookie_header: str
    running_nana: str
    running_main_open_key: str
    running_login_iden_no: str

    @classmethod
    def empty(cls) -> "DonggukSessionState":
        return cls(cookie_header="", running_nana="", running_main_open_key="", running_login_iden_no="")


def _parse_runtime_fields(post_data: str | None) -> dict[str, str]:
    if not post_data:
        return {}
    return {key: value for key, value in parse_qsl(post_data, keep_blank_values=True)}


@dataclass(slots=True)
class DonggukBrowserBootstrap:
    target: BrowserBootstrapTarget
    settings: BrowserBootstrapSettings

    @staticmethod
    def _looks_like_missing_browser_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "executable doesn't exist" in message
            or "browsertype.launch" in message
            or "please run the following command" in message
        )

    def resolve_session_state(self) -> DonggukSessionState:
        return run_sync_in_playwright_worker(self._resolve_session_state_sync)

    def _resolve_session_state_sync(self) -> DonggukSessionState:
        try:
            playwright_sync_api = importlib.import_module("playwright.sync_api")
        except ImportError as exc:
            raise BrowserBootstrapError(
                "Playwright is not installed. Install project dependencies and run 'playwright install chromium'."
            ) from exc

        playwright_timeout_error = getattr(playwright_sync_api, "TimeoutError")
        playwright_error = getattr(playwright_sync_api, "Error")
        sync_playwright = getattr(playwright_sync_api, "sync_playwright")

        selector = self.settings.ready_selector_override or self.target.ready_selector
        click_selector = self.settings.click_selector_override or self.target.click_selector
        deadline = time.monotonic() + (self.settings.timeout_ms / 1000)
        runtime_fields: dict[str, str] = {}

        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=self.settings.browser == "headless")
                except playwright_error as exc:
                    if not self.settings.auto_install_browser or not self._looks_like_missing_browser_error(exc):
                        raise
                    ensure_playwright_chromium_installed()
                    browser = playwright.chromium.launch(headless=self.settings.browser == "headless")

                context = browser.new_context()
                page = context.new_page()

                def capture_runtime(request: Any) -> None:
                    if not str(request.url).endswith(LOAD_PATH_SUFFIX):
                        return
                    runtime_fields.update(_parse_runtime_fields(request.post_data))

                page.on("request", capture_runtime)

                try:
                    page.goto(self.target.entry_url, wait_until="domcontentloaded", timeout=self.settings.timeout_ms)
                    if selector:
                        page.wait_for_selector(selector, timeout=self.settings.timeout_ms)
                    if click_selector:
                        page.locator(click_selector).click(timeout=self.settings.timeout_ms)
                    while time.monotonic() < deadline:
                        cookies = {item["name"]: item["value"] for item in context.cookies() if item.get("value")}
                        if (
                            all(cookies.get(name) for name in self.target.required_cookie_names)
                            and runtime_fields.get("_runningNana")
                            and runtime_fields.get("_runningMainOpenKey")
                            and runtime_fields.get("_runningLoginIdenNo")
                        ):
                            return DonggukSessionState(
                                cookie_header=serialize_cookie_header(cookies, self.target.required_cookie_names),
                                running_nana=runtime_fields["_runningNana"],
                                running_main_open_key=runtime_fields["_runningMainOpenKey"],
                                running_login_iden_no=runtime_fields["_runningLoginIdenNo"],
                            )
                        page.wait_for_timeout(250)
                finally:
                    context.close()
                    browser.close()
        except playwright_timeout_error as exc:
            raise BrowserBootstrapError(
                "Playwright bootstrap timed out before the required Dongguk session state was available."
            ) from exc
        except playwright_error as exc:
            raise BrowserBootstrapError(f"Playwright bootstrap failed: {exc}") from exc

        raise BrowserBootstrapError("Playwright bootstrap finished without acquiring the required Dongguk session state.")
