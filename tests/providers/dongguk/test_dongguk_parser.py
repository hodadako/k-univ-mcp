from k_univ_mcp.providers.dongguk.models import DonggukCourseRow, DonggukDepartmentRow
from k_univ_mcp.providers.dongguk.parser import build_course, parse_meeting_slots


def test_parse_meeting_slots_preserves_fractional_period_warnings() -> None:
    slots, warnings = parse_meeting_slots("월, 수 2.5교시(10:30) ~ 3.5교시(12:00)")
    assert slots == []
    assert warnings == ["Unparsed fractional period: 2.5", "Unparsed fractional period: 3.5"]


def test_parse_meeting_slots_handles_integer_period_ranges() -> None:
    slots, warnings = parse_meeting_slots("화, 목 4교시(12:00) ~ 5교시(13:30)")
    assert warnings == []
    assert [(slot.day_code, slot.period) for slot in slots] == [("TUE", 4), ("TUE", 5), ("THU", 4), ("THU", 5)]


def test_department_row_prefers_codes_and_names_from_full_path() -> None:
    row = DonggukDepartmentRow.from_payload(
        {
            "DPT_CD": "DS030412",
            "DEPT_NM_FULL": "[서울]사회과학대학>광고홍보학과",
            "DEPT_LVL_CD": "CM040.30",
            "DEPT_NM": "광고홍보학과",
            "CAMPUS_CD": "CM030.10",
            "ORGN_CLSF_CD": "CM015.110",
            "USE_YN": "Y",
            "COLG_CD": "DS0304",
        }
    )

    assert row.code == "DS030412"
    assert row.name == "광고홍보학과"
    assert row.campus_code == "CM030.10"
    assert row.college_code == "DS0304"


def test_build_course_maps_core_fields() -> None:
    course = build_course(
        DonggukCourseRow(
            {
                "SBJ_NO": "COR101",
                "DVCLS": "01",
                "SBJ_NM": "기초수학",
                "SBJ_ENG_NM": "Basic Mathematics",
                "PROF_KOR_DSC": "홍길동",
                "PROF_ENG_DSC": "Hong Gil-dong",
                "TMTBL_KOR_DSC": "화, 목 4교시(12:00) ~ 5교시(13:30)",
                "TMTBL_ENG_DSC": "Tue, Thu 4~5",
                "ROOM_KOR_DSC": "A101",
                "ROOM_ENG_DSC": "A101",
                "LESN_REGN_CD_NM": "서울",
                "CPDIV_CD_NM": "전공",
                "OBJ_SCHGRD": "1",
                "CDT": "3",
                "THRY_HCNT": "3",
                "LESN_STY_CD": "강의",
                "RECOD_EVAL_METH_CD": "상대평가",
                "OPEN_DPTMJR_CD": "DS030412",
                "DPT_NM": "광고홍보학과",
            }
        ),
        year="2026",
        semester="CM160.10",
        campus_code="CM030.10",
        campus_name="서울",
        college_code="DS0304",
        college_name="사회과학대학",
        department_code="DS030412",
        department_name="광고홍보학과",
    )

    assert course.provider == "dongguk"
    assert course.course_key == "COR101-01"
    assert course.term_name == "1학기"
    assert course.meeting_slots[0].day_code == "TUE"
    assert course.meeting_slots[1].day_code == "TUE"
    assert course.department_code == "DS030412"
    assert course.department_name == "광고홍보학과"
