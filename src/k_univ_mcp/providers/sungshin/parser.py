from __future__ import annotations

from __future__ import annotations

from typing import TYPE_CHECKING

from k_univ_mcp.models import Course

if TYPE_CHECKING:
    from k_univ_mcp.providers.sungshin.models import SungshinCourseRow


def build_course(
    row: SungshinCourseRow,
    *,
    year: str,
    semester: str,
) -> Course:
    payload = row.payload
    credits = payload.get("cdtHcnt", "").split("/")[0] if payload.get("cdtHcnt") else None

    return Course(
        provider="sungshin",
        year=year,
        semester=semester,
        term_name=payload.get("semCd"),
        campus_code=payload.get("cmpCd", ""),
        campus_name=payload.get("cmpCdNm"),
        university_code=payload.get("orgClsfCd", ""),
        university_name=payload.get("crsNm"),
        faculty_code=payload.get("dptMjrCd", ""),
        faculty_name=payload.get("opDptmjrNm"),
        course_code=row.course_code,
        section=row.section,
        course_key=f"{row.course_code}-{row.section}",
        title=row.title,
        title_english=row.title_english,
        professor_name=row.professor_name,
        professor_name_english=None,
        lecture_time_raw=row.lecture_time_raw,
        lecture_time_english_raw=None,
        classroom=payload.get("roomKorDsc"),
        classroom_english=None,
        campus_display_name=payload.get("cmpCdNm"),
        completion_division_name=payload.get("cpdivNm"),
        recommended_year=None,
        credits=credits,
        recognized_hours=None,
        course_class_name=payload.get("sbjMngNm"),
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=None,
        established_department_code=payload.get("dptMjrCd"),
        established_department_name=payload.get("opDptmjrNm"),
        meeting_slots=[],
        parse_warnings=[],
        raw=payload,
    )
