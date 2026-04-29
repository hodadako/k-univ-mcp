import asyncio

from k_univ_mcp.browser_bootstrap import (
    BrowserBootstrapError,
    ensure_playwright_chromium_installed,
    run_sync_in_playwright_worker,
    serialize_cookie_header,
)
from k_univ_mcp.providers.yonsei.bootstrap import EnvCookieBootstrap, YonseiBootstrapError, parse_cookie_header


def test_parse_cookie_header_extracts_required_keys() -> None:
    cookies = parse_cookie_header("JSESSIONID=abc; NetFunnel_ID=def; foo=bar")
    assert cookies["JSESSIONID"] == "abc"
    assert cookies["NetFunnel_ID"] == "def"
    assert cookies["foo"] == "bar"


def test_env_bootstrap_requires_jsessionid() -> None:
    bootstrap = EnvCookieBootstrap("JSESSIONID=abc")
    assert bootstrap.resolve_cookie_header() == "JSESSIONID=abc"


def test_env_bootstrap_allows_empty_netfunnel_value() -> None:
    bootstrap = EnvCookieBootstrap("JSESSIONID=abc; NetFunnel_ID=")
    assert bootstrap.resolve_cookie_header() == "JSESSIONID=abc; NetFunnel_ID="


def test_env_bootstrap_rejects_missing_jsessionid() -> None:
    bootstrap = EnvCookieBootstrap("NetFunnel_ID=abc")
    try:
        bootstrap.resolve_cookie_header()
    except YonseiBootstrapError as exc:
        assert "JSESSIONID" in str(exc)
    else:
        raise AssertionError("Expected bootstrap to reject a cookie header without JSESSIONID.")


def test_serialize_cookie_header_preserves_required_cookie_order() -> None:
    cookie_header = serialize_cookie_header(
        {"other": "keep", "NetFunnel_ID": "net", "JSESSIONID": "session"},
        ("JSESSIONID", "NetFunnel_ID"),
    )
    assert cookie_header.startswith("JSESSIONID=session; NetFunnel_ID=net")
    assert "other=keep" in cookie_header


def test_serialize_cookie_header_requires_expected_cookie_names() -> None:
    try:
        serialize_cookie_header({"JSESSIONID": "session"}, ("JSESSIONID", "NetFunnel_ID"))
    except BrowserBootstrapError as exc:
        assert "NetFunnel_ID" in str(exc)
    else:
        raise AssertionError("Expected browser bootstrap serialization to reject missing required cookies.")


def test_ensure_playwright_chromium_installed_raises_on_failure(monkeypatch) -> None:
    class Result:
        returncode = 1
        stdout = ""
        stderr = "install failed"

    monkeypatch.setattr("k_univ_mcp.browser_bootstrap.subprocess.run", lambda *args, **kwargs: Result())
    try:
        ensure_playwright_chromium_installed()
    except BrowserBootstrapError as exc:
        assert "install failed" in str(exc)
    else:
        raise AssertionError("Expected automatic browser installation failure to raise BrowserBootstrapError.")


def test_run_sync_in_playwright_worker_runs_directly_without_event_loop() -> None:
    assert run_sync_in_playwright_worker(lambda: "ok") == "ok"


def test_run_sync_in_playwright_worker_uses_worker_thread_inside_event_loop() -> None:
    async def main() -> tuple[bool, str]:
        def probe() -> tuple[bool, str]:
            try:
                _ = asyncio.get_running_loop()
            except RuntimeError:
                return True, "ok"
            return False, "loop-present"

        return run_sync_in_playwright_worker(probe)

    assert asyncio.run(main()) == (True, "ok")
