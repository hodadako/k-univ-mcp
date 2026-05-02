from __future__ import annotations

from k_univ_mcp.providers.hanyang.models import HanyangCourseRow
from k_univ_mcp.providers.hanyang.parser import build_course, parse_meeting_slots


def test_parse_meeting_slots():
    slots = parse_meeting_slots("월(1-2) 수(3)")
    assert [(slot.day_code, slot.period) for slot in slots] == [
        ("MON", 1),
        ("MON", 2),
        ("WED", 3),
    ]

    slots = parse_meeting_slots("화(4-6)")
    assert [(slot.day_code, slot.period) for slot in slots] == [
        ("TUE", 4),
        ("TUE", 5),
        ("TUE", 6),
    ]

    assert parse_meeting_slots(None) == []


def test_build_course():
    raw = {
        "suupNo": "12345",
        "haksuNo": "HANYANG01",
        "gwamokNm": "테스트 강의",
        "gwamokEnm": "Test Course",
        "daepyo_gangsa_nm": "홍길동",
        "suupTimes": "월(1-2)",
        "suupRoomNms": "공학관 101호",
        "hakjeom": 3,
        "isuGbNm": "전공핵심",
        "banGrade": 2,
        "campusNm": "서울",
        "jojikGbNm": "공과대학",
    }
    row = HanyangCourseRow(raw)
    course = build_course(row, year="2026", semester="10", org_code="H0002256")

    assert course.provider == "hanyang"
    assert course.course_code == "HANYANG01"
    assert course.title == "테스트 강의"
    assert course.professor_name == "홍길동"
    assert course.credits == "3"
    assert len(course.meeting_slots) == 2
    assert course.meeting_slots[0].day_code == "MON"
    assert course.meeting_slots[0].period == 1
