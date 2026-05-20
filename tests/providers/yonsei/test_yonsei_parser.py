from k_univ_mcp.providers.yonsei.models import YonseiCourseRow
from k_univ_mcp.providers.yonsei.parser import build_course, parse_meeting_slots


def test_parse_meeting_slots_supports_day_continuation_tokens() -> None:
    slots, warnings = parse_meeting_slots("월1-2,3/화4")

    assert warnings == []
    assert [(slot.day_code, slot.period) for slot in slots] == [
        ("MON", 1),
        ("MON", 2),
        ("MON", 3),
        ("TUE", 4),
    ]


def test_build_course_maps_yonsei_fields() -> None:
    course = build_course(
        YonseiCourseRow(
            {
                "subjtnb": "YON101",
                "corseDvclsNo": "01",
                "subjtnbCorsePrcts": "YON101-01",
                "subjtNm": "연세세미나",
                "subjtEngNm": "Yonsei Seminar",
                "cgprfNm": "홍길동",
                "cgprfEngNm": "Hong Gil-dong",
                "lctreTimeNm": "월1-2,3/화4",
                "lctreTimeEngNm": "Mon 1-3 / Tue 4",
                "lecrmNm": "백양관 101",
                "lecrmEngNm": "Baekyang Hall 101",
                "campsDivNm": "신촌",
                "subsrtDivNm": "전공선택",
                "hy": "1",
                "cdt": "3",
                "rcognHrs": "3",
                "subjtClNm": "이론",
                "gradeEvlMthdDivNm": "상대평가",
                "rmvlcYn": "N",
                "rmvlcYnNm": "정상",
                "estblDeprtCd": "D001",
                "estblDeprtNm": "컴퓨터과학과",
                "syySmtDivNm": "2026-1학기",
            }
        ),
        year="2026",
        semester="10",
        campus_code="sinchon-undergraduate",
        campus_name="신촌캠퍼스 학부",
        college_code="C001",
        college_name="공과대학",
        department_code="D001",
        department_name="컴퓨터과학과",
    )

    assert course.provider == "yonsei"
    assert course.course_key == "YON101-01"
    assert course.classroom == "백양관 101"
    assert course.professor_name_english == "Hong Gil-dong"
    assert course.semester_name == "1학기"
    assert [(slot.day_code, slot.period) for slot in course.meeting_slots] == [
        ("MON", 1),
        ("MON", 2),
        ("MON", 3),
        ("TUE", 4),
    ]
