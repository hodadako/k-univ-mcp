from __future__ import annotations

import re
from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.providers.hanyang.models import HanyangCourseRow


def parse_meeting_slots(time_raw: str | None) -> list[MeetingSlot]:
    if not time_raw:
        return []

    slots: list[MeetingSlot] = []
    # Hanyang time format example: "월(1-2) 수(3)"
    # This is a common format, but let's try a simple regex
    day_map = {
        "월": "MON",
        "화": "TUE",
        "수": "WED",
        "목": "THU",
        "금": "FRI",
        "토": "SAT",
        "일": "SUN",
    }

    # matches "월(1-2)" or "수(3)"
    pattern = re.compile(r"([월화수목금토일])\((\d+)(?:-(\d+))?\)")
    matches = pattern.finditer(time_raw)

    for match in matches:
        day_text = match.group(1)
        start_period = int(match.group(2))
        end_period = int(match.group(3)) if match.group(3) else start_period

        day_code = day_map.get(day_text, "UNKNOWN")
        for period in range(start_period, end_period + 1):
            slots.append(
                MeetingSlot(
                    day_code=day_code,
                    day_name=day_text,
                    period=period,
                )
            )

    return slots


def build_course(
    row: HanyangCourseRow,
    *,
    year: str,
    semester: str,
    campus_code: str,
    campus_name: str | None = None,
) -> Course:
    meeting_slots = parse_meeting_slots(row.suup_times)

    return Course(
        provider="hanyang",
        year=year,
        semester=semester,
        semester_name=row.semester_name,
        campus_code=campus_code,
        campus_name=campus_name or row.campus_nm,
        college_code=row.jojik_gb_nm or "",
        college_name=row.jojik_gb_nm,
        department_code=row.slg_sosok_cd or "",
        department_name=row.slg_sosok_nm,
        course_code=row.haksu_no,
        section=row.suup_no,
        course_key=f"{row.haksu_no}-{row.suup_no}" if row.haksu_no and row.suup_no else None,
        title=row.gwamok_nm,
        title_english=row.gwamok_enm,
        professor_name=row.daepyo_gangsa_nm,
        professor_name_english=None,
        lecture_time_raw=row.suup_times,
        lecture_time_english_raw=None,
        classroom=row.suup_room_nms,
        classroom_english=None,
        campus_display_name=campus_name or row.campus_nm,
        completion_division_name=row.isu_gb_nm,
        recommended_year=row.ban_grade,
        credits=row.hakjeom,
        recognized_hours=None,
        course_class_name=None,
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=None,
        established_department_code=None,
        established_department_name=None,
        meeting_slots=meeting_slots,
        raw=row.raw,
    )
