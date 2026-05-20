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
    # Test that 2nd semester returns empty results as requested
    assert service.get_courses("2026", "2", "inmun", "all", "all") == []
    courses, raw = service.collect_courses(year="2026", semester="2")
    assert courses == []
    assert raw == []

def test_myongji_client_find_article_id_patterns():
    client = MyongjiClient()

    # Mock HTML response for the notice board
    mock_html = """
    <html>
        <body>
            <a href="/bbs/mjukr/143/231868/artclView.do">2026학년도 하계 계절수업 안내(수강신청 및 등록)</a>
            <a href="/bbs/mjukr/143/229374/artclView.do">2026학년도 편입생 오리엔테이션 안내</a>
            <a href="/bbs/mjukr/143/227302/artclView.do">2025학년도 동계 계절수업 안내(수강신청 및 등록)</a>
        </body>
    </html>
    """

    with patch.object(MyongjiClient, '_get', return_value=mock_html):
        assert client.find_article_id("2026", "summer") == "231868"
        assert client.find_article_id("2026", "1") == "229374"
        assert client.find_article_id("2025", "winter") == "227302"
        assert client.find_article_id("2026", "winter") is None

def test_myongji_client_get_pdf_download_url():
    client = MyongjiClient()

    # Mock HTML response for article view
    mock_html = """
    <html>
        <body>
            <div class="attachments">
                <li><a href="/bbs/mjukr/143/177349/download.do">(붙임2)2026-하계 계절수업 안내문.hwp</a></li>
                <li><a href="/bbs/mjukr/143/177439/download.do">(붙임1)2026-하계 계절수업 개설강좌 시간표_0519.pdf</a></li>
            </div>
        </body>
    </html>
    """

    with patch.object(MyongjiClient, '_get', return_value=mock_html):
        expected_url = "https://www.mju.ac.kr/bbs/mjukr/143/177439/download.do"
        assert client.get_pdf_download_url("231868") == expected_url

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
        professor="홍길동"
    )

    course = build_course(row, year="2026", semester="1")

    assert course.campus_code == "inmun"
    assert course.college_name == "인문대학"
    assert course.title == "국어학개론"
    assert course.course_code == "KOR101"
    assert course.lecture_time_raw == "월1,2,3"
    assert course.classroom == "S1234"

def test_myongji_parser_build_course_combined_time_room():
    from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
    from k_univ_mcp.providers.myongji.parser import build_course

    row = MyongjiCourseRow(
        campus="자연",
        title="미적분학1",
        lecture_time="화1,2,3 (함박관 201)",
        classroom=None
    )

    course = build_course(row, year="2026", semester="1")
    assert course.campus_code == "jayeon"
    assert course.lecture_time_raw == "화1,2,3"
    assert course.classroom == "함박관 201"
