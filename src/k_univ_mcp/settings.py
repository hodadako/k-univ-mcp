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

    @classmethod
    def from_env(cls, *, load_env: bool = True) -> "AppSettings":
        if load_env:
            load_dotenv()
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
        )
