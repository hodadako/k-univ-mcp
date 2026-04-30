from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppSettings:
    yonsei_cookie: str | None
    yonsei_referer: str
    yonsei_timeout: int
    yonsei_retry_total: int
    yonsei_retry_backoff: float
    yonsei_sleep_seconds: float
    enable_browser_bootstrap: bool
    browser_bootstrap_on_start: bool
    browser: Literal["headless", "headed"]
    browser_bootstrap_timeout_ms: int
    browser_ready_selector: str | None
    browser_click_selector: str | None
    auto_install_playwright_browser: bool
    yonsei_session_refresh_retries: int
    output_dir: Path
    mcp_transport: Literal["stdio", "sse", "streamable-http"]
    yonsei_seed_root: Path | None = None
    dongguk_cookie: str | None = None
    dongguk_seoul_cookie: str | None = None
    dongguk_wise_cookie: str | None = None
    dongguk_enable_browser_bootstrap: bool = True
    dongguk_referer: str = "https://support.dongguk.edu/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039"
    dongguk_timeout: int = 30
    dongguk_retry_total: int = 3
    dongguk_retry_backoff: float = 0.5
    dongguk_sleep_seconds: float = 0.2
    dongguk_session_refresh_retries: int = 1
    dongguk_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    gachon_cookie: str | None = None
    gachon_timeout: int = 30
    gachon_retry_total: int = 3
    gachon_retry_backoff: float = 0.5
    gachon_sleep_seconds: float = 0.2
    gachon_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    inha_timeout: int = 30
    inha_sleep_seconds: float = 0.5

    @classmethod
    def from_env(cls, *, load_env: bool = True) -> "AppSettings":
        if load_env:
            _ = load_dotenv()
        raw_transport = os.getenv("K_UNIV_MCP_TRANSPORT", "stdio")
        if raw_transport not in {"stdio", "sse", "streamable-http"}:
            raise ValueError("K_UNIV_MCP_TRANSPORT must be one of: stdio, sse, streamable-http.")
        raw_browser = os.getenv("BROWSER", "headless")
        if raw_browser not in {"headless", "headed"}:
            raise ValueError("BROWSER must be one of: headless, headed.")
        return cls(
            yonsei_cookie=os.getenv("YONSEI_COOKIE"),
            yonsei_referer=os.getenv(
                "YONSEI_REFERER",
                "https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko",
            ),
            yonsei_timeout=int(os.getenv("YONSEI_TIMEOUT", "30")),
            yonsei_retry_total=int(os.getenv("YONSEI_RETRY_TOTAL", "3")),
            yonsei_retry_backoff=float(os.getenv("YONSEI_RETRY_BACKOFF", "0.5")),
            yonsei_sleep_seconds=float(os.getenv("YONSEI_SLEEP_SECONDS", "0.2")),
            enable_browser_bootstrap=_get_bool("ENABLE_BROWSER_BOOTSTRAP", False),
            browser_bootstrap_on_start=_get_bool("BROWSER_BOOTSTRAP_ON_START", False),
            browser=cast(Literal["headless", "headed"], raw_browser),
            browser_bootstrap_timeout_ms=int(os.getenv("BROWSER_BOOTSTRAP_TIMEOUT_MS", "30000")),
            browser_ready_selector=os.getenv("BROWSER_READY_SELECTOR"),
            browser_click_selector=os.getenv("BROWSER_CLICK_SELECTOR"),
            auto_install_playwright_browser=_get_bool("AUTO_INSTALL_PLAYWRIGHT_BROWSER", True),
            yonsei_session_refresh_retries=int(os.getenv("YONSEI_SESSION_REFRESH_RETRIES", "1")),
            output_dir=Path(os.getenv("K_UNIV_MCP_OUTPUT_DIR", "out")),
            mcp_transport=cast(Literal["stdio", "sse", "streamable-http"], raw_transport),
            yonsei_seed_root=Path(seed_root) if (seed_root := os.getenv("YONSEI_SEED_ROOT")) else None,
            dongguk_cookie=os.getenv("DONGGUK_COOKIE"),
            dongguk_seoul_cookie=os.getenv("DONGGUK_SEOUL_COOKIE"),
            dongguk_wise_cookie=os.getenv("DONGGUK_WISE_COOKIE"),
            dongguk_enable_browser_bootstrap=_get_bool(
                "DONGGUK_ENABLE_BROWSER_BOOTSTRAP",
                _get_bool("ENABLE_BROWSER_BOOTSTRAP", True),
            ),
            dongguk_referer=os.getenv(
                "DONGGUK_REFERER",
                "https://support.dongguk.edu/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039",
            ),
            dongguk_timeout=int(os.getenv("DONGGUK_TIMEOUT", "30")),
            dongguk_retry_total=int(os.getenv("DONGGUK_RETRY_TOTAL", "3")),
            dongguk_retry_backoff=float(os.getenv("DONGGUK_RETRY_BACKOFF", "0.5")),
            dongguk_sleep_seconds=float(os.getenv("DONGGUK_SLEEP_SECONDS", "0.2")),
            dongguk_session_refresh_retries=int(os.getenv("DONGGUK_SESSION_REFRESH_RETRIES", "1")),
            dongguk_user_agent=os.getenv(
                "DONGGUK_USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ),
            gachon_cookie=os.getenv("GACHON_COOKIE"),
            gachon_timeout=int(os.getenv("GACHON_TIMEOUT", "30")),
            gachon_retry_total=int(os.getenv("GACHON_RETRY_TOTAL", "3")),
            gachon_retry_backoff=float(os.getenv("GACHON_RETRY_BACKOFF", "0.5")),
            gachon_sleep_seconds=float(os.getenv("GACHON_SLEEP_SECONDS", "0.2")),
            gachon_user_agent=os.getenv(
                "GACHON_USER_AGENT",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            ),
            inha_timeout=int(os.getenv("INHA_TIMEOUT", "30")),
            inha_sleep_seconds=float(os.getenv("INHA_SLEEP_SECONDS", "0.5")),
        )
