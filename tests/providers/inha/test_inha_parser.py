from k_univ_mcp.providers.inha.models import InhaCourseRow
from k_univ_mcp.providers.inha.parser import build_course, parse_meeting_slots


def test_parse_meeting_slots_splits_multiple_days_and_skips_web_lectures() -> None:
    slots = parse_meeting_slots("월1,2,화3(5-101)")

    assert [(slot.day_code, slot.day_name, slot.period) for slot in slots] == [
        ("1", "월", 1),
        ("1", "월", 2),
        ("2", "화", 3),
    ]
    assert parse_meeting_slots("셀0(웹강의)") == []


def test_build_course_maps_inha_fields() -> None:
    course = build_course(
        InhaCourseRow(
            haksu_section="ME101-001",
            title="기계공학개론",
            grade="1",
            credits="3.0",
            category="전필",
            time_location="월1,2,3(5-101)",
            professor="홍길동",
            evaluation="상대평가",
            note="",
            raw={"raw_tds": []},
        ),
        year="2026",
        semester="10",
        campus_code="yonghyeon",
        campus_name="인하대학교 용현캠퍼스",
        college_code="공과대학",
        college_name="공과대학",
        department_code="0194002",
        department_name="기계공학과 / 기계공학",
    )

    assert course.provider == "inha"
    assert course.course_code == "ME101"
    assert course.section == "001"
    assert course.course_key == "ME101-001"
    assert course.department_code == "0194002"
    assert course.professor_name == "홍길동"
    assert [(slot.day_code, slot.period) for slot in course.meeting_slots] == [
        ("1", 1),
        ("1", 2),
        ("1", 3),
    ]
