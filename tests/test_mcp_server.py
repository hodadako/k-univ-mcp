from pathlib import Path

from k_univ_mcp.mcp_server import build_mcp_server, create_server
from k_univ_mcp.settings import AppSettings


def build_settings() -> AppSettings:
    return AppSettings(
        yonsei_cookie=None,
        yonsei_referer="https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko",
        yonsei_timeout=30,
        yonsei_retry_total=3,
        yonsei_retry_backoff=0.5,
        yonsei_sleep_seconds=0.0,
        enable_browser_bootstrap=False,
        browser_bootstrap_on_start=False,
        browser="headless",
        browser_bootstrap_timeout_ms=30000,
        browser_ready_selector=None,
        browser_click_selector=None,
        auto_install_playwright_browser=True,
        yonsei_session_refresh_retries=1,
        output_dir=Path("out"),
        mcp_transport="stdio",
        yonsei_seed_root=None,
    )


def test_mcp_server_factories_build_server() -> None:
    settings = build_settings()

    built = build_mcp_server(settings)
    created = create_server(settings)

    assert type(built) is type(created)
