from __future__ import annotations

import re

from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.semester import semester_display_name
from k_univ_mcp.providers.inha.models import InhaCourseRow

DAY_MAP = {
    "월": "1",
    "화": "2",
    "수": "3",
    "목": "4",
    "금": "5",
    "토": "6",
    "일": "7",
}


def parse_meeting_slots(time_location: str) -> list[MeetingSlot]:
    # Example: "월1,2,3(5-101)", "월1,2,화3(5-101)", "셀0(웹강의)"
    slots: list[MeetingSlot] = []
    if not time_location or "웹강의" in time_location:
        return slots

    # Simple parser for "DayPeriods(Room)" format
    # This is a best-effort parser.
    # Pattern: ([월화수목금토일])([\d,]+)
    matches = re.finditer(r"([월화수목금토일])([\d,]+)", time_location)
    for match in matches:
        day_name = match.group(1)
        day_code = DAY_MAP.get(day_name, "0")
        periods = match.group(2).split(",")
        for p in periods:
            if p.isdigit():
                slots.append(MeetingSlot(day_code=day_code, day_name=day_name, period=int(p)))

    return slots


def build_course(
    row: InhaCourseRow,
    *,
    year: str,
    semester: str,
    campus_code: str,
    campus_name: str | None,
    college_code: str,
    college_name: str | None,
    department_code: str,
    department_name: str | None,
) -> Course:
    meeting_slots = parse_meeting_slots(row.time_location)

    return Course(provider="inha",
    year=year, semester_code=semester, semester_name=semester_display_name(semester, year=year),
    campus_code=campus_code,
    campus_name=campus_name,
    college_code=college_code,
    college_name=college_name,
    department_code=department_code,
    department_name=department_name,
    course_code=row.course_code,
    section=row.section,
    course_key=row.haksu_section,
    title=row.title,
    title_english=None,
    professor_name=row.professor,
    professor_name_english=None,
    lecture_time_raw=row.time_location,
    lecture_time_english_raw=None,
    classroom=None,  # Extracting classroom from time_location if needed
    classroom_english=None,
    campus_display_name=campus_name,
    completion_division_name=row.category,
    recommended_year=row.grade,
    credits=row.credits,
    recognized_hours=None,
    course_class_name=None,
    evaluation_method_name=row.evaluation,
    cancelled=None,
    cancelled_label=None,
    established_department_code=department_code,
    established_department_name=department_name,
    meeting_slots=meeting_slots,
    raw=row.raw,)
