from dataclasses import dataclass, field, replace
from pathlib import Path

from k_univ_mcp.settings import AppSettings
from k_univ_mcp.providers.dongguk.bootstrap import DonggukSessionState
from k_univ_mcp.providers.dongguk.service import (
    DONGGUK_CAMPUS_ADAPTERS,
    DonggukCatalog,
    DonggukService,
    export_dongguk_courses,
    require_dongguk_export_batch_size,
)


@dataclass
class FakeClient:
    campus_code: str = "CM030.10"
    load_calls: int = 0
    course_calls: list[tuple[str, str, str, str, str]] = field(default_factory=list)

    def fetch_semesters(self):
        return [
            {
                "OPEN_YY": "2026",
                "OPEN_SEM_CD": "CM160.10",
                "OPEN_SEM_NM": "1학기",
            },
            {
                "OPEN_YY": "2026",
                "OPEN_SEM_CD": "CM160.20",
                "OPEN_SEM_NM": "2학기",
            },
        ]

    def load_course_page(self):
        self.load_calls += 1
        if self.campus_code == "CM030.21":
            return {
                "payload": [
                    {
                        "CAMPUS_CD": "CM030.21",
                        "CAMPUS_NM": "WISE",
                        "COLG_CD": "DK0101",
                        "DEPT_NM_FULL": "[WISE]인문대학",
                        "DEPT_NM": "인문대학",
                    },
                    {
                        "CAMPUS_CD": "CM030.21",
                        "COLG_CD": "DK0101",
                        "DEPT_LVL_CD": "CM040.30",
                        "DPT_CD": "DK010101",
                        "DEPT_NM_FULL": "[WISE]인문대학>국어국문학과",
                        "DEPT_NM": "국어국문학과",
                        "USE_YN": "Y",
                    },
                ]
            }
        return {
            "payload": [
                {
                    "CAMPUS_CD": "CM030.10",
                    "CAMPUS_NM": "서울",
                    "COLG_CD": "DS0304",
                    "DEPT_NM_FULL": "[서울]사회과학대학",
                    "DEPT_NM": "사회과학대학",
                },
                {
                    "CAMPUS_CD": "CM030.10",
                    "COLG_CD": "DS0304",
                    "DEPT_LVL_CD": "CM040.30",
                    "DPT_CD": "DS030412",
                    "DEPT_NM_FULL": "[서울]사회과학대학>광고홍보학과",
                    "DEPT_NM": "광고홍보학과",
                    "USE_YN": "Y",
                },
            ]
        }

    def list_courses(self, year: str, semester: str, campus_code: str, univ_code: str, faculty_code: str):
        self.course_calls.append((year, semester, campus_code, univ_code, faculty_code))
        return [
            {
                "SBJ_NO": "COR101",
                "DVCLS": "01",
                "SBJ_NM": "기초수학",
                "TMTBL_KOR_DSC": "화 4교시",
                "OPEN_DPTMJR_CD": faculty_code,
                "DPT_NM": "광고홍보학과",
            }
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


def test_catalog_builds_campus_university_and_faculty_rows() -> None:
    catalog = DonggukCatalog.from_payload(FakeClient().load_course_page())

    assert [campus.code for campus in catalog.campuses] == ["CM030.10"]
    assert catalog.campuses[0].name == "서울"
    assert [university.code for university in catalog.universities] == ["DS0304"]
    assert [faculty.code for faculty in catalog.faculties] == ["DS030412"]


def test_service_caches_load_payload_and_collects_courses() -> None:
    clients = {
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    }
    service = DonggukService(clients)

    campuses = service.get_campuses(year="2026", semester="CM160.10")
    universities = service.get_universities("CM030.10", year="2026", semester="CM160.10")
    faculties = service.get_faculties("CM030.10", "DS0304", year="2026", semester="CM160.10")
    courses, raw_payloads = service.collect_courses(year="2026", semester="CM160.10")

    assert campuses[0].code == "CM030.10"
    assert universities[0].code == "DS0304"
    assert faculties[0].code == "DS030412"
    assert len(courses) == 2
    assert len(raw_payloads) == 2
    assert clients["CM030.10"].load_calls == 1
    assert clients["CM030.21"].load_calls == 1
    assert clients["CM030.10"].course_calls == [("2026", "CM160.10", "CM030.10", "DS0304", "DS030412")]
    assert clients["CM030.21"].course_calls == [("2026", "CM160.10", "CM030.21", "DK0101", "DK010101")]


def test_service_resolves_numeric_semester_input_before_collecting_courses() -> None:
    clients = {
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    }
    service = DonggukService(clients)

    courses, raw_payloads = service.collect_courses(year="2026", semester="1")

    assert len(courses) == 2
    assert len(raw_payloads) == 2
    assert clients["CM030.10"].course_calls == [("2026", "CM160.10", "CM030.10", "DS0304", "DS030412")]
    assert clients["CM030.21"].course_calls == [("2026", "CM160.10", "CM030.21", "DK0101", "DK010101")]
    assert [payload.semester for payload in raw_payloads] == ["CM160.10", "CM160.10"]


def test_service_rejects_unavailable_semester_from_doload() -> None:
    service = DonggukService({"CM030.10": FakeClient(campus_code="CM030.10")})

    try:
        service.get_universities("CM030.10", year="2026", semester="3학기")
    except ValueError as exc:
        message = str(exc)
        assert "Available semesters from doLoad.do" in message
        assert "CM160.10 (1학기)" in message
        assert "CM160.20 (2학기)" in message
    else:
        raise AssertionError("Expected unavailable Dongguk semester to raise ValueError.")


def test_iter_course_batches_yields_per_faculty_batches() -> None:
    clients = {
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    }
    service = DonggukService(clients)

    batches = list(service.iter_course_batches(year="2026", semester="CM160.10"))

    assert len(batches) == 2
    assert [len(courses) for courses, _ in batches] == [1, 1]
    assert [raw_payloads[0].faculty_code for _, raw_payloads in batches] == ["DS030412", "DK010101"]


def test_iter_course_batches_can_select_a_batch_slice() -> None:
    clients = {
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    }
    service = DonggukService(clients)

    batches = list(service.iter_course_batches(year="2026", semester="CM160.10", batch_index=1, batch_size=1))

    assert len(batches) == 1
    assert batches[0][1][0].faculty_code == "DK010101"


def test_get_campuses_returns_static_seoul_and_wise() -> None:
    service = DonggukService({code: FakeClient(campus_code=code) for code in DONGGUK_CAMPUS_ADAPTERS})

    campuses = service.get_campuses(year="2026", semester="CM160.10")

    assert [(campus.code, campus.name) for campus in campuses] == [("CM030.10", "서울"), ("CM030.21", "WISE")]


def test_service_filters_wise_catalog_by_selected_campus() -> None:
    service = DonggukService({
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    })

    universities = service.get_universities("CM030.21", year="2026", semester="CM160.10")
    faculties = service.get_faculties("CM030.21", "DK0101", year="2026", semester="CM160.10")

    assert [university.code for university in universities] == ["DK0101"]
    assert [faculty.code for faculty in faculties] == ["DK010101"]


def test_create_service_can_attach_browser_bootstrap(monkeypatch) -> None:
    bootstrap_calls: list[str] = []

    def fake_resolve_session_state(self) -> DonggukSessionState:
        bootstrap_calls.append("called")
        return DonggukSessionState(
            cookie_header="JSESSIONID=auto; locale=ko",
            running_nana="nana",
            running_main_open_key="open-key",
            running_login_iden_no="login-iden",
        )

    monkeypatch.setattr(
        "k_univ_mcp.providers.dongguk.service.DonggukBrowserBootstrap.resolve_session_state",
        fake_resolve_session_state,
    )

    from k_univ_mcp.providers.dongguk.service import create_dongguk_service

    service = create_dongguk_service(build_settings())

    assert set(service.clients) == {"CM030.10", "CM030.21"}
    assert service.clients["CM030.10"].refresh_session_state is not None
    assert service.clients["CM030.21"].refresh_session_state is not None
    assert service.clients["CM030.10"].cookie_header is None
    assert bootstrap_calls == []


def test_create_service_can_disable_browser_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr(
        "k_univ_mcp.providers.dongguk.service.DonggukBrowserBootstrap.resolve_session_state",
        lambda self: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    from k_univ_mcp.providers.dongguk.service import create_dongguk_service

    service = create_dongguk_service(build_settings(dongguk_enable_browser_bootstrap=False))

    assert set(service.clients) == {"CM030.10", "CM030.21"}
    assert service.clients["CM030.10"].refresh_session_state is None
    assert service.clients["CM030.21"].refresh_session_state is None


def test_create_service_can_use_campus_specific_cookies() -> None:
    from k_univ_mcp.providers.dongguk.service import create_dongguk_service

    service = create_dongguk_service(
        build_settings(
            dongguk_seoul_cookie="JSESSIONID=seoul",
            dongguk_wise_cookie="JSESSIONID=wise",
        )
    )

    assert service.clients["CM030.10"].cookie_header == "JSESSIONID=seoul"
    assert service.clients["CM030.21"].cookie_header == "JSESSIONID=wise"


def test_wise_adapter_uses_distinct_entry_path() -> None:
    assert DONGGUK_CAMPUS_ADAPTERS["CM030.10"].index_path != DONGGUK_CAMPUS_ADAPTERS["CM030.21"].index_path
    assert "654867724D6E564B57577777554374315558647861564273646A524251543039" in DONGGUK_CAMPUS_ADAPTERS["CM030.21"].index_path


def test_require_dongguk_export_batch_size_accepts_positive_values() -> None:
    assert require_dongguk_export_batch_size(25) == 25


def test_require_dongguk_export_batch_size_rejects_missing_or_non_positive_values() -> None:
    for value in (None, 0, -1):
        try:
            require_dongguk_export_batch_size(value)
        except ValueError as exc:
            assert "requires a positive batch_size" in str(exc)
        else:
            raise AssertionError("Expected invalid Dongguk batch size to raise ValueError.")


def test_export_dongguk_courses_runs_all_batches_and_merges(monkeypatch) -> None:
    clients = {
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    }
    service = DonggukService(clients)
    exported_batches: list[tuple[str, list[str]]] = []
    merged_dirs: list[str] = []

    def fake_export_course_batches(course_batches, outdir, stem):
        batches = list(course_batches)
        exported_batches.append((str(outdir), [raw_payloads[0].faculty_code for _, raw_payloads in batches]))
        return ({"jsonl": f"{outdir}/{stem}.jsonl"}, sum(len(courses) for courses, _ in batches))

    def fake_merge_exported_batches(batch_dirs, outdir, stem):
        merged_dirs.extend(str(path) for path in batch_dirs)
        return ({"jsonl": f"{outdir}/{stem}.jsonl"}, 2)

    monkeypatch.setattr("k_univ_mcp.providers.dongguk.service.export_course_batches", fake_export_course_batches)
    monkeypatch.setattr("k_univ_mcp.providers.dongguk.service.merge_exported_batches", fake_merge_exported_batches)

    result = export_dongguk_courses(
        service,
        year="2026",
        semester="CM160.10",
        outdir=Path("merged-out"),
        batch_size=1,
    )

    assert [path for path, _ in exported_batches] == ["merged-out/batch-0", "merged-out/batch-1"]
    assert merged_dirs == ["merged-out/batch-0", "merged-out/batch-1"]
    assert result["row_count"] == 2
    assert result["batch_index"] is None
    assert result["total_batches"] == 2
    assert result["next_batch_index"] is None
    assert [batch_result["batch_index"] for batch_result in result["batch_results"]] == [0, 1]


def test_export_dongguk_courses_keeps_single_batch_mode_when_batch_index_is_set(monkeypatch) -> None:
    service = DonggukService({
        "CM030.10": FakeClient(campus_code="CM030.10"),
        "CM030.21": FakeClient(campus_code="CM030.21"),
    })
    merge_calls: list[str] = []

    def fake_export_course_batches(course_batches, outdir, stem):
        batches = list(course_batches)
        return ({"jsonl": f"{outdir}/{stem}.jsonl"}, sum(len(courses) for courses, _ in batches))

    def fake_merge_exported_batches(batch_dirs, outdir, stem):
        merge_calls.append(str(outdir))
        return ({"jsonl": f"{outdir}/{stem}.jsonl"}, 0)

    monkeypatch.setattr("k_univ_mcp.providers.dongguk.service.export_course_batches", fake_export_course_batches)
    monkeypatch.setattr("k_univ_mcp.providers.dongguk.service.merge_exported_batches", fake_merge_exported_batches)

    result = export_dongguk_courses(
        service,
        year="2026",
        semester="CM160.10",
        outdir=Path("single-batch-out"),
        batch_index=0,
        batch_size=1,
    )

    assert result["batch_index"] == 0
    assert result["next_batch_index"] == 1
    assert merge_calls == []
