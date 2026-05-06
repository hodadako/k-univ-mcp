from __future__ import annotations

from typing import Any

from k_univ_mcp.models import Course

def build_course(
    row: dict[str, Any],
    *,
    year: str,
    semester: str,
) -> Course:
    credits = row.get("cdtHcnt", "").split("/")[0] if row.get("cdtHcnt") else None

    return Course(
        provider="sungshin",
        year=year,
        semester=semester,
        term_name=row.get("semCd"),
        campus_code=row.get("cmpCd", ""),
        campus_name=row.get("cmpCdNm"),
        college_code=row.get("orgClsfCd", ""),
        college_name=row.get("crsNm"),
        department_code=row.get("dptMjrCd", ""),
        department_name=row.get("opDptmjrNm"),
        course_code=row.get("sbjNo"),
        section=row.get("dvcls"),
        course_key=f"{row.get('sbjNo')}-{row.get('dvcls')}",
        title=row.get("sbjNm"),
        title_english=row.get("sbjEnm"),
        professor_name=row.get("profDsc"),
        professor_name_english=None,
        lecture_time_raw=row.get("tmtblKorDsc"),
        lecture_time_english_raw=None,
        classroom=row.get("roomKorDsc"),
        classroom_english=None,
        campus_display_name=row.get("cmpCdNm"),
        completion_division_name=row.get("cpdivNm"),
        recommended_year=None,
        credits=credits,
        recognized_hours=None,
        course_class_name=row.get("sbjMngNm"),
        evaluation_method_name=None,
        cancelled=None,
        cancelled_label=None,
        established_department_code=row.get("dptMjrCd"),
        established_department_name=row.get("opDptmjrNm"),
        meeting_slots=[],
        parse_warnings=[],
        raw=row,
    )
