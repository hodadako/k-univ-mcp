from dataclasses import replace
from pathlib import Path

from k_univ_mcp.providers.soongsil.models import SoongsilCatalogEntry
from k_univ_mcp.providers.soongsil.service import SoongsilService
from k_univ_mcp.settings import AppSettings


class FakeClient:
    entries: list[SoongsilCatalogEntry]
    html_by_department: dict[str, str]

    def __init__(self) -> None:
        self.list_calls: list[tuple[str, str]] = []
        self.collect_calls: list[tuple[str, str, list[tuple[str, str]]]] = []
        self.entries = [
            SoongsilCatalogEntry("11000001", "인문대학", "1100000101", "국어국문학과"),
            SoongsilCatalogEntry("12000001", "자연과학대학", "1200000101", "수학과"),
        ]
        self.html_by_department = {
            "1100000101": """
            <table id='WD0184' ct='ST'>
              <tbody id='WD0184-contentTBody'>
                <tr rt='2'>
                  <th>계획</th><th>이수구분(주전공)</th><th>이수구분(다전공)</th><th>공학인증</th>
                  <th>과목번호</th><th>과목명</th><th>수강유의사항</th><th>강좌유형정보</th>
                  <th>분반</th><th>교수명</th><th>개설학과</th><th>시간/학점(설계)</th>
                  <th>수강인원</th><th>여석</th><th>강의시간(강의실)</th><th>수강대상</th>
                </tr>
                <tr rt='1'>
                  <td></td><td>전기-국문</td><td></td><td></td><td>2150517201</td><td>국어연구의기초</td><td></td><td></td><td>01</td><td>오충연</td><td>국어국문학과</td><td>3.0/3.0</td><td>37</td><td>3</td><td>화 목 13:30-14:45</td><td>1학년 국문</td>
                </tr>
              </tbody>
            </table>
            """,
            "1200000101": """
            <table id='WD0184' ct='ST'>
              <tbody id='WD0184-contentTBody'>
                <tr rt='2'>
                  <th>계획</th><th>이수구분(주전공)</th><th>이수구분(다전공)</th><th>공학인증</th>
                  <th>과목번호</th><th>과목명</th><th>수강유의사항</th><th>강좌유형정보</th>
                  <th>분반</th><th>교수명</th><th>개설학과</th><th>시간/학점(설계)</th>
                  <th>수강인원</th><th>여석</th><th>강의시간(강의실)</th><th>수강대상</th>
                </tr>
                <tr rt='1'>
                  <td></td><td>전기-수학</td><td></td><td></td><td>MATH1001</td><td>미적분학</td><td></td><td></td><td>01</td><td>김교수</td><td>수학과</td><td>3.0/3.0</td><td>40</td><td>5</td><td>월 수 09:00-10:15</td><td>1학년</td>
                </tr>
              </tbody>
            </table>
            """,
        }

    def list_catalog(self, year: str, semester: str) -> list[SoongsilCatalogEntry]:
        self.list_calls.append((year, semester))
        return self.entries

    def collect_course_pages(
        self,
        year: str,
        semester: str,
        entries: list[SoongsilCatalogEntry],
    ) -> list[tuple[SoongsilCatalogEntry, str]]:
        self.collect_calls.append(
            (
                year,
                semester,
                [(entry.college_code, entry.department_code) for entry in entries],
            )
        )
        return [
            (entry, self.html_by_department[entry.department_code]) for entry in entries
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


def test_soongsil_service_builds_dynamic_universities_faculties_and_courses() -> None:
    client = FakeClient()
    service = SoongsilService(build_settings(), client=client)

    colleges = service.get_colleges("soongsil", year="2026", semester="1")
    departments = service.get_departments(
        "soongsil", "11000001", year="2026", semester="1"
    )
    courses, raw_payloads = service.collect_courses(year="2026", semester="1")

    assert [college.code for college in colleges] == ["11000001", "12000001"]
    assert [department.code for department in departments] == ["1100000101"]
    assert len(courses) == 2
    assert {course.course_code for course in courses} == {"2150517201", "MATH1001"}
    assert {course.semester_name for course in courses} == {"2026학년도 1학기"}
    assert len(raw_payloads) == 2
    assert client.list_calls == [("2026", "1학기")]
    assert client.collect_calls == [
        ("2026", "1학기", [("11000001", "1100000101"), ("12000001", "1200000101")])
    ]


def test_soongsil_service_can_filter_by_university_or_faculty_code() -> None:
    client = FakeClient()
    service = SoongsilService(build_settings(), client=client)

    by_university = service.get_courses(
        "2026", "1", "soongsil", "11000001", "soongsil_all"
    )
    by_faculty = service.get_courses(
        "2026", "1", "soongsil", "soongsil_all", "1200000101"
    )

    assert [course.course_code for course in by_university] == ["2150517201"]
    assert [course.course_code for course in by_faculty] == ["MATH1001"]
    assert by_university[0].semester_name == "2026학년도 1학기"
    assert by_faculty[0].semester_name == "2026학년도 1학기"


def test_soongsil_service_normalizes_unified_semester_labels() -> None:
    client = FakeClient()
    service = SoongsilService(build_settings(), client=client)

    service.collect_courses(year="2026", semester="summer")

    assert client.list_calls == [("2026", "여름학기")]
    assert client.collect_calls == [
        ("2026", "여름학기", [("11000001", "1100000101"), ("12000001", "1200000101")])
    ]
