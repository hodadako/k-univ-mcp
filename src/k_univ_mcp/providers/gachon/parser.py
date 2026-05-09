from __future__ import annotations

import re

from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.providers.gachon.models import GachonCourseRow

DAY_NAME_MAP = {
    "월": ("MON", "Monday"),
    "화": ("TUE", "Tuesday"),
    "수": ("WED", "Wednesday"),
    "목": ("THU", "Thursday"),
    "금": ("FRI", "Friday"),
    "토": ("SAT", "Saturday"),
    "일": ("SUN", "Sunday"),
}


def parse_meeting_slots(raw_text: str | None) -> tuple[list[MeetingSlot], list[str]]:
    if not raw_text:
        return [], []

    slots: list[MeetingSlot] = []
    warnings: list[str] = []
    for token in filter(None, (part.strip() for part in str(raw_text).split(","))):
        cleaned = token.replace(" ", "")
        match = re.fullmatch(r"([월화수목금토일])(\d+)", cleaned)
        if not match:
            warnings.append(f"Unparsed time token: {token}")
            continue
        day_token, period_token = match.groups()
        code, name = DAY_NAME_MAP[day_token]
        slots.append(MeetingSlot(day_code=code, day_name=name, period=int(period_token)))

    unique_slots: dict[tuple[str, int], MeetingSlot] = {(slot.day_code, slot.period): slot for slot in slots}
    return list(unique_slots.values()), warnings


def build_course(
    row: GachonCourseRow,
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
    meeting_slots, parse_warnings = parse_meeting_slots(row.lecture_time_raw)
    course_key = row.course_code
    if row.course_code and row.section:
        course_key = f"{row.course_code}-{row.section}"

    return Course(
        provider="gachon",
        year=year,
        semester=semester,
        semester_name=row.payload.get("TERM_NM") or semester,
        campus_code=campus_code,
        campus_name=campus_name,
        college_code=college_code,
        college_name=college_name,
        department_code=department_code,
        department_name=department_name,
        course_code=row.course_code,
        section=row.section,
        course_key=course_key,
        title=(row.title.strip() if row.title else None),
        title_english=None,
        professor_name=row.professor_name,
        professor_name_english=None,
        lecture_time_raw=row.lecture_time_raw,
        lecture_time_english_raw=None,
        classroom=row.payload.get("LOC_NM"),
        classroom_english=None,
        campus_display_name=None,
        completion_division_name=row.payload.get("ISU_NM"),
        recommended_year=row.payload.get("GRADE"),
        credits=row.payload.get("SISU"),
        recognized_hours=None,
        course_class_name=("online" if str(row.payload.get("CYBER_YN", "")).strip().upper() == "Y" else None),
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=None,
        established_department_code=department_code,
        established_department_name=row.payload.get("PRINT_DPT") or department_name,
        meeting_slots=meeting_slots,
        parse_warnings=parse_warnings,
        raw=row.payload,
    )
