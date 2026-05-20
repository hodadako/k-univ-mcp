from __future__ import annotations

import re

from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.semester import semester_display_name
from k_univ_mcp.providers.yonsei.models import YonseiCourseRow

DAY_NAME_MAP = {
    "월": ("MON", "Monday"),
    "화": ("TUE", "Tuesday"),
    "수": ("WED", "Wednesday"),
    "목": ("THU", "Thursday"),
    "금": ("FRI", "Friday"),
    "토": ("SAT", "Saturday"),
    "일": ("SUN", "Sunday"),
}


def _expand_periods(token: str) -> list[int]:
    if re.fullmatch(r"\d+", token):
        return [int(token)]
    if re.fullmatch(r"\d+-\d+", token):
        start, end = token.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return []


def parse_meeting_slots(raw_text: str | None) -> tuple[list[MeetingSlot], list[str]]:
    if not raw_text:
        return [], []

    cleaned = (
        raw_text.replace("(", "/")
        .replace(")", "")
        .replace(" ", "")
        .replace("·", ",")
        .replace(";", "/")
    )
    slots: list[MeetingSlot] = []
    warnings: list[str] = []
    current_day: str | None = None

    for segment in filter(None, cleaned.split("/")):
        for token in filter(None, segment.split(",")):
            match = re.fullmatch(r"([월화수목금토일])(\d+(?:-\d+)?)", token)
            if match:
                day_token = match.group(1)
                current_day = day_token
                for period in _expand_periods(match.group(2)):
                    code, name = DAY_NAME_MAP[day_token]
                    slots.append(MeetingSlot(day_code=code, day_name=name, period=period))
                continue

            if current_day and re.fullmatch(r"\d+(?:-\d+)?", token):
                for period in _expand_periods(token):
                    code, name = DAY_NAME_MAP[current_day]
                    slots.append(MeetingSlot(day_code=code, day_name=name, period=period))
                continue

            warnings.append(f"Unparsed time token: {token}")

    unique_slots: dict[tuple[str, int], MeetingSlot] = {(slot.day_code, slot.period): slot for slot in slots}
    return list(unique_slots.values()), warnings


def build_course(
    row: YonseiCourseRow,
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
    meeting_slots, parse_warnings = parse_meeting_slots(row.payload.get("lctreTimeNm"))
    return Course(provider="yonsei",
    year=year, semester_code=semester, semester_name=semester_display_name(row.payload.get("syySmtDivNm") or semester),
    campus_code=campus_code,
    campus_name=campus_name,
    college_code=college_code,
    college_name=college_name,
    department_code=department_code,
    department_name=department_name,
    course_code=row.course_code,
    section=row.section,
    course_key=row.payload.get("subjtnbCorsePrcts"),
    title=row.title,
    title_english=row.title_english,
    professor_name=row.professor_name,
    professor_name_english=row.payload.get("cgprfEngNm"),
    lecture_time_raw=row.payload.get("lctreTimeNm"),
    lecture_time_english_raw=row.payload.get("lctreTimeEngNm"),
    classroom=row.payload.get("lecrmNm"),
    classroom_english=row.payload.get("lecrmEngNm"),
    campus_display_name=row.payload.get("campsDivNm"),
    completion_division_name=row.payload.get("subsrtDivNm"),
    recommended_year=row.payload.get("hy"),
    credits=row.payload.get("cdt"),
    recognized_hours=row.payload.get("rcognHrs"),
    course_class_name=row.payload.get("subjtClNm"),
    evaluation_method_name=row.payload.get("gradeEvlMthdDivNm"),
    cancelled=row.payload.get("rmvlcYn"),
    cancelled_label=row.payload.get("rmvlcYnNm"),
    established_department_code=row.payload.get("estblDeprtCd"),
    established_department_name=row.payload.get("estblDeprtNm"),
    meeting_slots=meeting_slots,
    parse_warnings=parse_warnings,
    raw=row.payload,)
