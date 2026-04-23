from __future__ import annotations

import importlib
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Literal, Protocol


class BrowserBootstrapError(RuntimeError):
    pass


class BrowserCookieCollector(Protocol):
    def collect(self, target: "BrowserBootstrapTarget", settings: "BrowserBootstrapSettings") -> dict[str, str]: ...


@dataclass(slots=True, frozen=True)
class BrowserBootstrapTarget:
    entry_url: str
    required_cookie_names: tuple[str, ...]
    ready_selector: str | None = None
    click_selector: str | None = None


@dataclass(slots=True, frozen=True)
class BrowserBootstrapSettings:
    enabled: bool = False
    browser: Literal["headless", "headed"] = "headless"
    timeout_ms: int = 30_000
    ready_selector_override: str | None = None
    click_selector_override: str | None = None
    auto_install_browser: bool = True


def serialize_cookie_header(cookies: dict[str, str], required_cookie_names: tuple[str, ...]) -> str:
    missing = [name for name in required_cookie_names if not cookies.get(name)]
    if missing:
        raise BrowserBootstrapError(
            f"Browser bootstrap did not acquire required cookies: {', '.join(missing)}."
        )

    ordered_pairs = [f"{name}={cookies[name]}" for name in required_cookie_names]
    extras = [f"{name}={value}" for name, value in cookies.items() if name not in required_cookie_names and value]
    return "; ".join(ordered_pairs + extras)


def ensure_playwright_chromium_installed() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        raise BrowserBootstrapError(f"Automatic Playwright Chromium install failed: {details}")


@dataclass(slots=True)
class PlaywrightCookieCollector:
    @staticmethod
    def _looks_like_missing_browser_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return (
            "executable doesn't exist" in message
            or "browsertype.launch" in message
            or "please run the following command" in message
        )

    def collect(self, target: BrowserBootstrapTarget, settings: BrowserBootstrapSettings) -> dict[str, str]:
        try:
            playwright_sync_api = importlib.import_module("playwright.sync_api")
        except ImportError as exc:
            raise BrowserBootstrapError(
                "Playwright is not installed. Install project dependencies and run 'playwright install chromium'."
            ) from exc

        playwright_timeout_error = getattr(playwright_sync_api, "TimeoutError")
        playwright_error = getattr(playwright_sync_api, "Error")
        sync_playwright = getattr(playwright_sync_api, "sync_playwright")
        selector = settings.ready_selector_override or target.ready_selector
        click_selector = settings.click_selector_override or target.click_selector
        deadline = time.monotonic() + (settings.timeout_ms / 1000)

        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=settings.browser == "headless")
                except playwright_error as exc:
                    if not settings.auto_install_browser or not self._looks_like_missing_browser_error(exc):
                        raise
                    ensure_playwright_chromium_installed()
                    browser = playwright.chromium.launch(headless=settings.browser == "headless")
                context = browser.new_context()
                page = context.new_page()
                try:
                    page.goto(target.entry_url, wait_until="domcontentloaded", timeout=settings.timeout_ms)
                    if selector:
                        page.wait_for_selector(selector, timeout=settings.timeout_ms)
                    if click_selector:
                        page.locator(click_selector).click(timeout=settings.timeout_ms)
                        page.wait_for_load_state("networkidle", timeout=settings.timeout_ms)
                    while time.monotonic() < deadline:
                        cookies = {item["name"]: item["value"] for item in context.cookies() if item.get("value")}
                        if all(cookies.get(name) for name in target.required_cookie_names):
                            return cookies
                        page.wait_for_timeout(250)
                finally:
                    context.close()
                    browser.close()
        except playwright_timeout_error as exc:
            raise BrowserBootstrapError(
                "Playwright bootstrap timed out before the required session cookies were available."
            ) from exc
        except playwright_error as exc:
            raise BrowserBootstrapError(f"Playwright bootstrap failed: {exc}") from exc

        raise BrowserBootstrapError("Playwright bootstrap finished without acquiring the required session cookies.")


@dataclass(slots=True)
class SeleniumCookieCollector:
    def collect(self, target: BrowserBootstrapTarget, settings: BrowserBootstrapSettings) -> dict[str, str]:
        raise NotImplementedError("Selenium bootstrap is not implemented yet. Use the Playwright backend for now.")


@dataclass(slots=True)
class BrowserSessionBootstrap:
    target: BrowserBootstrapTarget
    settings: BrowserBootstrapSettings
    backend: Literal["playwright", "selenium"] = "playwright"

    def resolve_cookie_header(self) -> str:
        if not self.settings.enabled:
            raise BrowserBootstrapError("Browser bootstrap is disabled.")

        collector: BrowserCookieCollector
        if self.backend == "playwright":
            collector = PlaywrightCookieCollector()
        else:
            collector = SeleniumCookieCollector()

        cookies = collector.collect(self.target, self.settings)
        return serialize_cookie_header(cookies, self.target.required_cookie_names)
