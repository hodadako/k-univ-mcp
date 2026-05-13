from dataclasses import dataclass, field, replace
from pathlib import Path

from k_univ_mcp.providers.yonsei.client import YonseiTransportError
from k_univ_mcp.browser_bootstrap import BrowserBootstrapSettings, BrowserBootstrapTarget
from k_univ_mcp.providers.yonsei.service import (
    YONSEI_CLICK_SELECTOR,
    YONSEI_READY_SELECTOR,
    YonseiSeedCatalog,
    YonseiService,
    create_yonsei_service,
)
from k_univ_mcp.settings import AppSettings


@dataclass
class FakeClient:
    def list_campuses(self, year: str, semester: str):
        return [{"deptCd": "s1", "deptNm": "신촌캠퍼스", "engDeptNm": "Sinchon Campus"}]

    def list_universities(self, year: str, semester: str, campus_code: str):
        return [{"deptCd": "s1103", "deptNm": "이과대학", "engDeptNm": "College of Science"}]

    def list_faculties(self, year: str, semester: str, campus_code: str, college_code: str):
        return [{"deptCd": "0301", "deptNm": "수학전공", "engDeptNm": "Mathematics", "sysinstDivCd": "H1"}]

    def list_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str):
        return [
            {
                "subjtnb": "MATH1001",
                "corseDvclsNo": "01",
                "subjtNm": "미적분학",
                "lctreTimeNm": "월1,2",
                "cgprfNm": "홍길동",
            }
        ]


@dataclass
class RecordingClient(FakeClient):
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def list_campuses(self, year: str, semester: str):
        self.calls.append(("campuses", year, semester))
        return super().list_campuses(year, semester)

    def list_universities(self, year: str, semester: str, campus_code: str):
        self.calls.append(("colleges", year, semester, campus_code))
        return super().list_universities(year, semester, campus_code)

    def list_faculties(self, year: str, semester: str, campus_code: str, college_code: str):
        self.calls.append(("departments", year, semester, campus_code, college_code))
        return super().list_faculties(year, semester, campus_code, college_code)

    def list_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str):
        self.calls.append(("courses", year, semester, campus_code, college_code, department_code))
        return super().list_courses(year, semester, campus_code, college_code, department_code)


@dataclass
class FallbackClient(FakeClient):
    def list_campuses(self, year: str, semester: str):
        raise YonseiTransportError("live campuses unavailable")

    def list_universities(self, year: str, semester: str, campus_code: str):
        raise YonseiTransportError("live colleges unavailable")


def test_service_requires_explicit_semester_for_faculties() -> None:
    service = YonseiService(FakeClient(), YonseiSeedCatalog())

    try:
        service.get_departments("sinchon-undergraduate", "s1103", year="", semester="10")
    except ValueError as exc:
        assert "must be passed explicitly" in str(exc)
    else:
        raise AssertionError("Expected explicit semester validation to reject empty year.")


def test_service_uses_explicit_semester_for_faculties() -> None:
    service = YonseiService(FakeClient(), YonseiSeedCatalog())
    departments = service.get_departments("sinchon-undergraduate", "s1103", year="2026", semester="10")
    assert departments[0].code == "0301"


def test_get_campuses_prefers_live_discovery() -> None:
    service = YonseiService(FakeClient(), YonseiSeedCatalog())

    campuses = service.get_campuses(year="2026", semester="10")

    assert [campus.code for campus in campuses] == ["sinchon-undergraduate"]
    assert campuses[0].name == "신촌캠퍼스 학부"


def test_get_universities_prefers_live_discovery() -> None:
    service = YonseiService(FakeClient(), YonseiSeedCatalog())

    colleges = service.get_colleges("sinchon-undergraduate", year="2026", semester="10")

    assert [college.code for college in colleges] == ["s1103"]
    assert colleges[0].name == "이과대학"


def test_get_campuses_falls_back_to_seed_when_live_discovery_fails() -> None:
    service = YonseiService(None, YonseiSeedCatalog())

    campuses = service.get_campuses(year="2026", semester="10")

    assert len(campuses) >= 1
    assert any(campus.code == "sinchon-undergraduate" for campus in campuses)
    assert any(campus.code == "sinchon-undergraduate" and campus.name == "신촌캠퍼스 학부" for campus in campuses)


def test_get_universities_falls_back_to_seed_when_live_discovery_fails() -> None:
    service = YonseiService(None, YonseiSeedCatalog())

    colleges = service.get_colleges("sinchon-undergraduate", year="2026", semester="10")

    assert len(colleges) >= 1
    assert any(college.code == "s1103" for college in colleges)


def test_get_campuses_requires_explicit_semester_even_for_seed_fallback() -> None:
    service = YonseiService(None, YonseiSeedCatalog())

    try:
        service.get_campuses(year="", semester="10")
    except ValueError as exc:
        assert "must be passed explicitly" in str(exc)
    else:
        raise AssertionError("Expected explicit semester validation for seeded campuses.")


def test_get_universities_requires_explicit_semester_even_for_seed_fallback() -> None:
    service = YonseiService(None, YonseiSeedCatalog())

    try:
        service.get_colleges("sinchon-undergraduate", year="2026", semester="")
    except ValueError as exc:
        assert "must be passed explicitly" in str(exc)
    else:
        raise AssertionError("Expected explicit semester validation for seeded colleges.")


def test_get_campuses_surfaces_live_discovery_failure_when_client_exists() -> None:
    service = YonseiService(FallbackClient(), YonseiSeedCatalog())

    try:
        service.get_campuses(year="2026", semester="10")
    except YonseiTransportError as exc:
        assert "live campuses unavailable" in str(exc)
    else:
        raise AssertionError("Expected live campus discovery failure to surface when a client is configured.")


def test_get_universities_surfaces_live_discovery_failure_when_client_exists() -> None:
    service = YonseiService(FallbackClient(), YonseiSeedCatalog())

    try:
        service.get_colleges("s1", year="2026", semester="10")
    except YonseiTransportError as exc:
        assert "live colleges unavailable" in str(exc)
    else:
        raise AssertionError("Expected live college discovery failure to surface when a client is configured.")


def test_collect_courses_builds_domain_objects() -> None:
    service = YonseiService(FakeClient(), YonseiSeedCatalog())
    courses, raw_payloads = service.collect_courses(
        year="2026",
        semester="10",
        campus_code="sinchon-undergraduate",
        college_code="s1103",
    )
    assert len(courses) == 1
    assert courses[0].title == "미적분학"
    assert courses[0].campus_name == "신촌캠퍼스 학부"
    assert len(raw_payloads) == 1


def test_collect_courses_uses_live_discovery_by_default() -> None:
    client = RecordingClient()
    service = YonseiService(client, YonseiSeedCatalog())

    courses, raw_payloads = service.collect_courses(year="2026", semester="10")

    assert len(courses) == 1
    assert len(raw_payloads) == 1
    assert client.calls == [
        ("campuses", "2026", "10"),
        ("colleges", "2026", "10", "s1"),
        ("departments", "2026", "10", "s1", "s1103"),
        ("courses", "2026", "10", "s1", "s1103", "0301"),
    ]


def test_service_normalizes_unified_semester_before_client_calls() -> None:
    client = RecordingClient()
    service = YonseiService(client, YonseiSeedCatalog())

    service.get_courses("2026", "1", "sinchon-undergraduate", "s1103", "0301")

    assert client.calls == [
        ("campuses", "2026", "10"),
        ("colleges", "2026", "10", "s1"),
        ("departments", "2026", "10", "s1", "s1103"),
        ("courses", "2026", "10", "s1", "s1103", "0301"),
    ]


def test_collect_courses_normalizes_unified_semester_before_export_fetch() -> None:
    client = RecordingClient()
    service = YonseiService(client, YonseiSeedCatalog())

    courses, raw_payloads = service.collect_courses(year="2026", semester="1")

    assert len(courses) == 1
    assert len(raw_payloads) == 1
    assert raw_payloads[0].semester == "10"
    assert courses[0].semester == "10"
    assert client.calls == [
        ("campuses", "2026", "10"),
        ("colleges", "2026", "10", "s1"),
        ("departments", "2026", "10", "s1", "s1103"),
        ("courses", "2026", "10", "s1", "s1103", "0301"),
    ]


def build_settings(**overrides: object) -> AppSettings:
    return replace(
        AppSettings(
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
        ),
        **overrides,
    )


def test_create_service_uses_manual_cookie_before_browser_bootstrap(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_cookie_header(self) -> str:
        bootstrap_calls.append("called")
        return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap.resolve_cookie_header", fake_resolve_cookie_header)
    service = create_yonsei_service(
        build_settings(
            yonsei_cookie="JSESSIONID=manual; NetFunnel_ID=manual",
            enable_browser_bootstrap=True,
        )
    )

    assert service.client is not None
    assert service.client.cookie_header == "JSESSIONID=manual; NetFunnel_ID=manual"
    assert bootstrap_calls == []


def test_create_service_can_seed_client_from_browser_bootstrap(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_cookie_header(self) -> str:
        bootstrap_calls.append("called")
        return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap.resolve_cookie_header", fake_resolve_cookie_header)
    service = create_yonsei_service(build_settings(enable_browser_bootstrap=True))

    assert service.client is not None
    assert service.client.cookie_header == ""
    assert bootstrap_calls == []
    assert service.client.refresh_cookie_header is not None


def test_create_service_does_not_eagerly_launch_browser_bootstrap(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_cookie_header(self) -> str:
        bootstrap_calls.append("called")
        return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap.resolve_cookie_header", fake_resolve_cookie_header)
    service = create_yonsei_service(build_settings(enable_browser_bootstrap=True))

    assert service.client is not None
    assert service.client.refresh_cookie_header is not None
    assert bootstrap_calls == []


def test_create_service_can_warmup_browser_bootstrap_on_start(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_cookie_header(self) -> str:
        bootstrap_calls.append("called")
        return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap.resolve_cookie_header", fake_resolve_cookie_header)
    service = create_yonsei_service(
        build_settings(
            enable_browser_bootstrap=True,
            browser_bootstrap_on_start=True,
        )
    )

    assert service.client is not None
    assert service.client.cookie_header == "JSESSIONID=auto; NetFunnel_ID=auto"
    assert bootstrap_calls == ["called"]


def test_manual_cookie_still_beats_startup_browser_warmup(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_cookie_header(self) -> str:
        bootstrap_calls.append("called")
        return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap.resolve_cookie_header", fake_resolve_cookie_header)
    service = create_yonsei_service(
        build_settings(
            yonsei_cookie="JSESSIONID=manual; NetFunnel_ID=manual",
            enable_browser_bootstrap=True,
            browser_bootstrap_on_start=True,
        )
    )

    assert service.client is not None
    assert service.client.cookie_header == "JSESSIONID=manual; NetFunnel_ID=manual"
    assert bootstrap_calls == []


def test_create_service_applies_yonsei_default_selectors(monkeypatch) -> None:
    captured_target: BrowserBootstrapTarget | None = None
    captured_settings: BrowserBootstrapSettings | None = None

    class FakeBrowserSessionBootstrap:
        def __init__(self, *, target, settings, backend="playwright") -> None:
            nonlocal captured_target, captured_settings
            captured_target = target
            captured_settings = settings

        def resolve_cookie_header(self) -> str:
            return "JSESSIONID=auto; NetFunnel_ID=auto"

    monkeypatch.setattr("k_univ_mcp.providers.yonsei.service.BrowserSessionBootstrap", FakeBrowserSessionBootstrap)
    create_yonsei_service(build_settings(enable_browser_bootstrap=True))

    assert captured_target is not None
    assert captured_settings is not None
    target = captured_target
    settings = captured_settings
    assert target.ready_selector == YONSEI_READY_SELECTOR
    assert target.click_selector == YONSEI_CLICK_SELECTOR
    assert settings.ready_selector_override is None
    assert settings.click_selector_override is None
