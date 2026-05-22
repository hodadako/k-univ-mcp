from __future__ import annotations

import io
from typing import Any

import pdfplumber

from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.providers.myongji.models import MyongjiCourseRow
from k_univ_mcp.semester import semester_display_name


def _normalize_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).replace("\n", " ").split())
    return text or None


def _normalize_display_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = _normalize_cell(value)
    if normalized is None:
        return None

    replacements = {
        "전 공": "전공",
        "세미 나": "세미나",
        "조 화": "조화",
        "선 택": "선택",
        "대 학": "대학",
        "학 과": "학과",
        "공 학": "공학",
    }
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return normalized


def _full_row_value(raw: dict[str, Any] | None, index: int) -> str | None:
    if not raw:
        return None
    values = raw.get("full_row")
    if not isinstance(values, list) or index >= len(values):
        return None
    return _normalize_cell(values[index])


def _lecture_blocks_from_full_row(raw: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None

    values = raw.get("full_row")
    if not isinstance(values, list):
        return None, None

    blocks: list[str] = []
    rooms: list[str] = []
    for start in (19, 22, 25):
        day = _normalize_cell(values[start]) if start < len(values) else None
        time = _normalize_cell(values[start + 1]) if start + 1 < len(values) else None
        room = _normalize_cell(values[start + 2]) if start + 2 < len(values) else None
        if day and time:
            block = f"{day} {time}"
            if room:
                block = f"{block} {room}"
                if room not in rooms:
                    rooms.append(room)
            blocks.append(block)

    lecture_time_raw = " / ".join(blocks) if blocks else None
    classroom = ", ".join(rooms) if rooms else None
    return lecture_time_raw, classroom


def parse_pdf(pdf_bytes: bytes) -> list[MyongjiCourseRow]:
    """Parse Myongji University course PDF and return structured course rows."""
    rows: list[MyongjiCourseRow] = []
    last_col_map: dict[str, int] = {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue

                header_index = -1
                for index, row in enumerate(table):
                    normalized_cells = [_normalize_cell(cell) for cell in row]
                    if any(cell and ("학수번호" in cell or "교과목명" in cell) for cell in normalized_cells):
                        header_index = index
                        break

                if header_index != -1:
                    header = table[header_index]
                    data_rows = table[header_index + 1 :]
                    col_map: dict[str, int] = {}
                    for idx, col in enumerate(header):
                        normalized = _normalize_cell(col)
                        if normalized:
                            col_map[normalized] = idx
                    if col_map:
                        last_col_map = col_map
                else:
                    if not last_col_map:
                        continue
                    col_map = last_col_map
                    data_rows = table

                def get_val(row: list[Any], names: list[str], default: Any = None):
                    for name in names:
                        if name in col_map:
                            idx = col_map[name]
                            if idx < len(row):
                                value = _normalize_cell(row[idx])
                                return value if value is not None else default
                    return default

                for row in data_rows:
                    if not any(_normalize_cell(cell) for cell in row):
                        continue

                    normalized_full_row = [_normalize_cell(cell) for cell in row]
                    row_obj = MyongjiCourseRow(
                        campus=get_val(row, ["캠퍼스", "캠퍼스구분"]),
                        college=get_val(row, ["대학"]),
                        department=get_val(row, ["학과(부)", "학과", "개설학과", "전공"]),
                        course_code=get_val(row, ["학수번호"]),
                        section=get_val(row, ["분반"]),
                        title=get_val(row, ["교과목명"]),
                        credits=get_val(row, ["학점"]),
                        hours=get_val(row, ["주당시간", "시간"]),
                        recommended_year=get_val(row, ["대상학년", "학년"]),
                        completion_division=get_val(row, ["이수구분"]),
                        professor=get_val(row, ["교수명", "담당교수"]),
                        lecture_time=get_val(row, ["강의시간/강의실", "강의시간", "시간"]),
                        classroom=get_val(row, ["강의실"]),
                        note=get_val(row, ["비고"]),
                        raw={"full_row": normalized_full_row},
                    )

                    if row_obj.course_code or row_obj.title:
                        rows.append(row_obj)

    return rows


def build_course(
    row: MyongjiCourseRow,
    *,
    year: str,
    semester: str,
) -> Course:
    raw_row = row.raw or {}

    campus_name = _normalize_display_text(row.campus or _full_row_value(raw_row, 11)) or "공통"
    campus_code = "inmun" if "인문" in campus_name else "jayeon" if "자연" in campus_name else "common"

    college_name = _normalize_display_text(row.college or _full_row_value(raw_row, 12))
    department_name = _normalize_display_text(row.department or _full_row_value(raw_row, 13))
    course_code = row.course_code or _full_row_value(raw_row, 3)
    section = row.section or _full_row_value(raw_row, 2)
    title = _normalize_display_text(row.title or _full_row_value(raw_row, 4))
    professor_name = _normalize_display_text(row.professor or _full_row_value(raw_row, 10))
    credits = row.credits or _full_row_value(raw_row, 14)
    recognized_hours = row.hours or _full_row_value(raw_row, 15)
    course_class_name = _normalize_display_text(_full_row_value(raw_row, 6))

    lecture_time_raw = row.lecture_time
    classroom = row.classroom
    fallback_lecture_time_raw, fallback_classroom = _lecture_blocks_from_full_row(raw_row)
    lecture_time_raw = lecture_time_raw or fallback_lecture_time_raw
    classroom = classroom or fallback_classroom or _full_row_value(raw_row, 17)

    if lecture_time_raw and not row.classroom and classroom is None and "(" in lecture_time_raw and lecture_time_raw.endswith(")"):
        parts = lecture_time_raw.rsplit("(", 1)
        lecture_time_raw = parts[0].strip()
        classroom = parts[1].rstrip(")").strip()

    course_key = None
    if course_code and section:
        course_key = f"{course_code}-{section}"

    college_code = college_name or "unknown"
    department_code = department_name or "unknown"

    return Course(
        provider="myongji",
        year=year,
        semester_code=semester,
        semester_name=semester_display_name(semester),
        campus_code=campus_code,
        campus_name=campus_name,
        college_code=college_code,
        college_name=college_name,
        department_code=department_code,
        department_name=department_name,
        course_code=course_code,
        section=section,
        course_key=course_key,
        title=title,
        title_english=None,
        professor_name=professor_name,
        professor_name_english=None,
        lecture_time_raw=lecture_time_raw,
        lecture_time_english_raw=None,
        classroom=classroom,
        classroom_english=None,
        campus_display_name=campus_name,
        completion_division_name=_normalize_display_text(row.completion_division),
        recommended_year=row.recommended_year,
        credits=credits,
        recognized_hours=recognized_hours,
        course_class_name=course_class_name,
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=_full_row_value(raw_row, 5),
        established_department_code=department_code,
        established_department_name=department_name,
        meeting_slots=[],
        parse_warnings=[],
        raw=raw_row,
    )
