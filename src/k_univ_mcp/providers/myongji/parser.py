from __future__ import annotations

import io
from typing import Any

import pdfplumber
from k_univ_mcp.models import Course, MeetingSlot
from k_univ_mcp.providers.myongji.models import MyongjiCourseRow

def parse_pdf(pdf_bytes: bytes) -> list[MyongjiCourseRow]:
    """
    Parse Myongji University course PDF and return a list of MyongjiCourseRow.
    """
    rows: list[MyongjiCourseRow] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            # The first few rows might be headers.
            # We need to identify the header row to map columns correctly.
            # Typical headers: 캠퍼스, 대학, 학과(부), 전공, 학수번호, 분반, 교과목명, 학점, ...

            header_index = -1
            for i, row in enumerate(table):
                if any(row) and ("학수번호" in str(row) or "교과목명" in str(row)):
                    header_index = i
                    break

            if header_index == -1:
                # If no header found on this page, maybe it's a continuation page.
                # Use a default mapping or skip.
                # For simplicity, let's assume if it has many columns, it's data.
                if len(table[0]) > 5:
                    data_rows = table
                else:
                    continue
            else:
                header = table[header_index]
                data_rows = table[header_index + 1:]

                # Create a mapping from header name to index
                col_map = {}
                for idx, col in enumerate(header):
                    if not col: continue
                    col_name = str(col).replace("\n", "").strip()
                    col_map[col_name] = idx

            # Process data rows
            for r in data_rows:
                if not any(r): continue

                # Check if it's likely a course row (e.g. has a course code or title)
                # This needs to be robust as PDF tables can be messy.

                row_data = {}
                # Map columns based on common names
                # 캠퍼스, 대학, 학과(부), 전공, 학수번호, 분반, 교과목명, 학점, 주당시간, 대상학년, 이수구분, 교수명, 강의시간/강의실, 비고

                # We'll use a heuristic if col_map isn't perfectly matched
                def get_val(names: list[str], default: Any = None):
                    for name in names:
                        if name in col_map:
                            val = r[col_map[name]]
                            return str(val).strip() if val is not None else default
                    return default

                row_obj = MyongjiCourseRow(
                    campus=get_val(["캠퍼스", "캠퍼스구분"]),
                    college=get_val(["대학"]),
                    department=get_val(["학과(부)", "학과", "개설학과"]),
                    course_code=get_val(["학수번호"]),
                    section=get_val(["분반"]),
                    title=get_val(["교과목명"]),
                    credits=get_val(["학점"]),
                    hours=get_val(["주당시간", "시간"]),
                    recommended_year=get_val(["대상학년", "학년"]),
                    completion_division=get_val(["이수구분"]),
                    professor=get_val(["교수명", "담당교수"]),
                    lecture_time=get_val(["강의시간/강의실", "강의시간", "시간"]),
                    classroom=get_val(["강의실"]),
                    note=get_val(["비고"]),
                    raw={"full_row": r}
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
    # Handle campus name and code
    campus_name = row.campus or "공통"
    campus_code = "inmun" if "인문" in campus_name else "jayeon" if "자연" in campus_name else "common"

    # Split lecture_time and classroom if they are combined
    lecture_time_raw = row.lecture_time
    classroom = row.classroom

    if lecture_time_raw and not classroom:
        # Often combined as "Mon 1,2 (Room 101)" or similar
        # This part needs fine-tuning based on actual PDF samples
        if "(" in lecture_time_raw and lecture_time_raw.endswith(")"):
            parts = lecture_time_raw.rsplit("(", 1)
            lecture_time_raw = parts[0].strip()
            classroom = parts[1].rstrip(")").strip()

    return Course(
        provider="myongji",
        year=year,
        semester=semester,
        semester_name=None, # Will be filled by common logic if needed
        campus_code=campus_code,
        campus_name=campus_name,
        college_code=row.college or "unknown",
        college_name=row.college,
        department_code=row.department or "unknown",
        department_name=row.department,
        course_code=row.course_code,
        section=row.section,
        course_key=None,
        title=row.title,
        title_english=None,
        professor_name=row.professor,
        professor_name_english=None,
        lecture_time_raw=lecture_time_raw,
        lecture_time_english_raw=None,
        classroom=classroom,
        classroom_english=None,
        campus_display_name=campus_name,
        completion_division_name=row.completion_division,
        recommended_year=row.recommended_year,
        credits=row.credits,
        recognized_hours=row.hours,
        course_class_name=None,
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=None,
        established_department_code=row.department,
        established_department_name=row.department,
        meeting_slots=[], # Parsing this from raw string is complex, leaving empty for now
        parse_warnings=[],
        raw=row.raw or {}
    )
