from __future__ import annotations

import re

from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.providers.dongguk.models import DonggukCourseRow

DAY_NAME_MAP = {
    "월": ("MON", "Monday"),
    "화": ("TUE", "Tuesday"),
    "수": ("WED", "Wednesday"),
    "목": ("THU", "Thursday"),
    "금": ("FRI", "Friday"),
    "토": ("SAT", "Saturday"),
    "일": ("SUN", "Sunday"),
}

SEMESTER_LABELS = {
    "CM160.10": "1학기",
    "CM160.11": "여름학기",
    "CM160.20": "2학기",
    "CM160.21": "겨울학기",
    "CM160.99": "공통학기",
}


def _unique_in_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _extract_periods(raw_text: str) -> tuple[list[int], list[str]]:
    periods: list[int] = []
    warnings: list[str] = []
    for token in re.findall(r"(\d+(?:\.\d+)?)\s*교시", raw_text):
        if "." in token:
            warnings.append(f"Unparsed fractional period: {token}")
            continue
        periods.append(int(token))

    if periods:
        return periods, warnings

    if ":" in raw_text:
        return [], warnings or [f"Unparsed time token: {raw_text}"]

    for token in re.findall(r"(\d+(?:\.\d+)?)", raw_text):
        if "." in token:
            warnings.append(f"Unparsed fractional period: {token}")
            continue
        periods.append(int(token))
    return periods, warnings


def parse_meeting_slots(raw_text: str | None) -> tuple[list[MeetingSlot], list[str]]:
    if not raw_text:
        return [], []

    days = _unique_in_order(re.findall(r"[월화수목금토일]", raw_text))
    if not days:
        return [], [f"Unparsed time token: {raw_text}"]

    periods, warnings = _extract_periods(raw_text)
    if not periods:
        return [], warnings or [f"Unparsed time token: {raw_text}"]

    slots: list[MeetingSlot] = []
    for day in days:
        code, name = DAY_NAME_MAP[day]
        for period in periods:
            slots.append(MeetingSlot(day_code=code, day_name=name, period=period))

    unique_slots: dict[tuple[str, int], MeetingSlot] = {(slot.day_code, slot.period): slot for slot in slots}
    return list(unique_slots.values()), warnings


def semester_label(semester: str | None) -> str | None:
    if not semester:
        return None
    return SEMESTER_LABELS.get(semester, semester)


def build_course(
    row: DonggukCourseRow,
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
    faculty_output_code = row.payload.get("OPEN_DPTMJR_CD") or department_code
    faculty_output_name = row.payload.get("DPT_NM") or department_name
    return Course(provider="dongguk",
    year=year, semester_code=semester, semester_name=semester_label(semester),
    campus_code=campus_code,
    campus_name=campus_name,
    college_code=college_code,
    college_name=college_name,
    department_code=str(faculty_output_code),
    department_name=faculty_output_name,
    course_code=row.course_code,
    section=row.section,
    course_key=f"{row.course_code}-{row.section}" if row.course_code and row.section else None,
    title=row.title,
    title_english=row.title_english,
    professor_name=row.professor_name,
    professor_name_english=row.professor_name_english,
    lecture_time_raw=row.lecture_time_raw,
    lecture_time_english_raw=row.lecture_time_english_raw,
    classroom=row.payload.get("ROOM_KOR_DSC"),
    classroom_english=row.payload.get("ROOM_ENG_DSC"),
    campus_display_name=row.payload.get("LESN_REGN_CD_NM"),
    completion_division_name=row.payload.get("CPDIV_CD_NM"),
    recommended_year=row.payload.get("OBJ_SCHGRD"),
    credits=row.payload.get("CDT"),
    recognized_hours=row.payload.get("THRY_HCNT"),
    course_class_name=row.payload.get("LESN_STY_CD"),
    evaluation_method_name=row.payload.get("RECOD_EVAL_METH_CD"),
    cancelled=None,
    cancelled_label=None,
    established_department_code=str(row.payload.get("OPEN_DPTMJR_CD") or department_code),
    established_department_name=row.payload.get("DPT_NM") or department_name,
    meeting_slots=meeting_slots,
    parse_warnings=parse_warnings,
    raw=row.payload,)
