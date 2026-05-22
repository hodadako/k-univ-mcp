from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from k_univ_mcp.providers.myongji.client import MyongjiClient
from k_univ_mcp.providers.myongji.service import MyongjiService


@pytest.fixture
def mock_client():
    return MagicMock(spec=MyongjiClient)


@pytest.fixture
def service(mock_client):
    return MyongjiService(client=mock_client)


def test_myongji_service_unsupported_semester(service):
    assert service.get_courses("2026", "2", "inmun", "all", "all") == []
    courses, raw = service.collect_courses(year="2026", semester="2")
    assert courses == []
    assert raw == []


def test_myongji_client_find_article_id_patterns():
    client = MyongjiClient()

    first_page_html = """
    <html>
        <body>
            <a href="/bbs/mjukr/143/231868/artclView.do">2026학년도 하계 계절수업 안내(수강신청 및 등록)</a>
        </body>
    </html>
    """
    third_page_html = """
    <html>
        <body>
            <a href="/bbs/mjukr/143/229374/artclView.do">2026학년도 편입생 오리엔테이션 안내</a>
            <a href="/bbs/mjukr/143/227302/artclView.do">2025학년도 동계 계절수업 안내(수강신청 및 등록)</a>
        </body>
    </html>
    """

    def fake_get(url, params=None):
        page = (params or {}).get("page", 1)
        if page == 3:
            return third_page_html
        return first_page_html

    with patch.object(MyongjiClient, "_get", side_effect=fake_get):
        assert client.find_article_id("2026", "summer") == "231868"
        assert client.find_article_id("2026", "1") == "229374"
        assert client.find_article_id("2025", "winter") == "227302"
        assert client.find_article_id("2026", "winter") is None


def test_myongji_client_get_pdf_download_url():
    client = MyongjiClient()

    mock_html = """
    <html>
        <body>
            <div class="attachments">
                <li><a href="/bbs/mjukr/143/175034/download.do">붙임 2026학년도 편입생 오리엔테이션 자료(학사지원팀).pdf</a></li>
                <li><a href="/bbs/mjukr/143/175035/download.do">2026-1학기 강의시간표_260220.xlsx.pdf</a></li>
            </div>
        </body>
    </html>
    """

    with patch.object(MyongjiClient, "_get", return_value=mock_html):
        expected_url = "https://www.mju.ac.kr/bbs/mjukr/143/175035/download.do"
        assert client.get_pdf_download_url("229374") == expected_url


def test_myongji_parser_build_course():
    from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
    from k_univ_mcp.providers.myongji.parser import build_course

    row = MyongjiCourseRow(
        campus="인문캠퍼스",
        college="인문대학",
        department="국어국문학과",
        course_code="KOR101",
        section="01",
        title="국어학개론",
        credits="3",
        lecture_time="월1,2,3",
        classroom="S1234",
        professor="홍길동",
    )

    course = build_course(row, year="2026", semester="1")

    assert course.campus_code == "inmun"
    assert course.college_name == "인문대학"
    assert course.title == "국어학개론"
    assert course.course_code == "KOR101"
    assert course.course_key == "KOR101-01"
    assert course.semester_name == "1학기"
    assert course.lecture_time_raw == "월1,2,3"
    assert course.classroom == "S1234"


def test_myongji_parser_build_course_combined_time_room():
    from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
    from k_univ_mcp.providers.myongji.parser import build_course

    row = MyongjiCourseRow(
        campus="자연",
        title="미적분학1",
        lecture_time="화1,2,3 (함박관 201)",
        classroom=None,
    )

    course = build_course(row, year="2026", semester="1")
    assert course.campus_code == "jayeon"
    assert course.lecture_time_raw == "화1,2,3"
    assert course.classroom == "함박관 201"


def test_myongji_parser_build_course_fills_fields_from_full_row_sample():
    from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
    from k_univ_mcp.providers.myongji.parser import build_course

    row = MyongjiCourseRow(
        raw={
            "full_row": [
                "2026",
                "1",
                "6246",
                "KMB02107",
                "인간심리의이해",
                "N",
                "이론",
                None,
                "55",
                None,
                "진성조",
                "인문",
                "명지대 교양",
                "인문교양",
                "3",
                "3",
                "0",
                "기인107",
                None,
                "화요일",
                "1500 - 1615",
                "S1217",
                "목요일",
                "1500 - 1615",
                "S1217",
                None,
                "-",
                None,
                None,
            ]
        }
    )

    course = build_course(row, year="2026", semester="1")

    assert course.semester_code == "1"
    assert course.semester_name == "1학기"
    assert course.campus_code == "inmun"
    assert course.campus_name == "인문"
    assert course.college_code == "명지대 교양"
    assert course.college_name == "명지대 교양"
    assert course.department_code == "인문교양"
    assert course.department_name == "인문교양"
    assert course.course_code == "KMB02107"
    assert course.section == "6246"
    assert course.course_key == "KMB02107-6246"
    assert course.title == "인간심리의이해"
    assert course.professor_name == "진성조"
    assert course.credits == "3"
    assert course.recognized_hours == "3"
    assert course.course_class_name == "이론"
    assert course.lecture_time_raw == "화요일 1500 - 1615 S1217 / 목요일 1500 - 1615 S1217"
    assert course.classroom == "S1217"
    assert course.cancelled_label == "N"


def test_myongji_parser_normalizes_suspicious_spacing_in_display_fields():
    from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
    from k_univ_mcp.providers.myongji.parser import build_course

    row = MyongjiCourseRow(
        title="4차산업혁명과미래사회진로선 택",
        college="미디어·휴먼라이프대 학",
        department="전기전자공학부 전기공학전 공",
        professor="진성조",
        raw={"full_row": []},
    )

    course = build_course(row, year="2026", semester="1")

    assert course.title == "4차산업혁명과미래사회진로선택"
    assert course.college_name == "미디어·휴먼라이프대학"
    assert course.department_name == "전기전자공학부 전기공학전공"
