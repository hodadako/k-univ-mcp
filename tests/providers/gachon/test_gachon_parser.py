from k_univ_mcp.providers.gachon.models import GachonCourseRow
from k_univ_mcp.providers.gachon.parser import build_course, parse_meeting_slots


def test_parse_meeting_slots_splits_comma_separated_periods() -> None:
    slots, warnings = parse_meeting_slots("수4 ,수5 ,수6")

    assert warnings == []
    assert [(slot.day_code, slot.period) for slot in slots] == [("WED", 4), ("WED", 5), ("WED", 6)]


def test_build_course_maps_gachon_fields() -> None:
    course = build_course(
        GachonCourseRow(
            {
                "HAKSU_NO": "CSE101",
                "SUBJECT_NM_KOR": " 자료구조 ",
                "PROFNM": "홍길동",
                "TIME": "수4 ,수5 ,수6",
                "LOC_NM": "A101",
                "ISU_NM": "전필",
                "PRINT_DPT": "컴퓨터공학과",
                "SISU": "3",
                "CYBER_YN": "Y",
            }
        ),
        year="2026",
        semester="10",
        campus_code="gachon",
        campus_name="가천대학교",
        university_code="COL01",
        university_name="AI대학",
        faculty_code="D001",
        faculty_name="컴퓨터공학과",
    )

    assert course.provider == "gachon"
    assert course.course_code == "CSE101"
    assert course.title == "자료구조"
    assert course.classroom == "A101"
    assert course.course_class_name == "online"
