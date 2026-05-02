from __future__ import annotations

from typing import Any
from k_univ_mcp.models import Campus, Course, Faculty, University, RawPayloadDump
from k_univ_mcp.providers.ssu.client import SsuClient
from k_univ_mcp.providers.ssu.parser import SsuParser
from k_univ_mcp.settings import AppSettings


class SsuService:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.client = SsuClient(
            timeout=settings.browser_bootstrap_timeout_ms // 1000,
            browser=settings.browser
        )
        self.parser = SsuParser()

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        return [Campus(code="ssu", name="숭실대학교", english_name="Soongsil University")]

    def get_universities(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[University]:
        return [University(campus_code=campus_code, code="ssu_all", name="전체")]

    def get_faculties(
        self,
        campus_code: str,
        univ_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Faculty]:
        return [Faculty(campus_code=campus_code, university_code=univ_code, code="ssu_all", name="전체")]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[Course]:
        html = self.client.fetch_course_html(year, semester)
        rows = self.parser.parse_courses(html)

        courses: list[Course] = []
        for row in rows:
            courses.append(Course(
                provider="ssu",
                year=year,
                semester=semester,
                term_name=None,
                campus_code=campus_code,
                campus_name="숭실대학교",
                university_code=univ_code,
                university_name=None,
                faculty_code=faculty_code,
                faculty_name=None,
                course_code=row.course_number,
                section=row.section,
                course_key=f"{row.course_number}-{row.section}",
                title=row.course_name,
                title_english=None,
                professor_name=row.professor,
                professor_name_english=None,
                lecture_time_raw=row.time_location,
                lecture_time_english_raw=None,
                classroom=None, # Parsed from time_location if needed
                classroom_english=None,
                campus_display_name=None,
                completion_division_name=row.completion_division_major,
                recommended_year=None,
                credits=row.time_credits.split("/")[1] if "/" in row.time_credits else None,
                recognized_hours=row.time_credits.split("/")[0] if "/" in row.time_credits else None,
                course_class_name=None,
                evaluation_method_name=None,
                cancelled=None,
                cancelled_label=None,
                established_department_code=None,
                established_department_name=row.department,
                raw=row.raw
            ))
        return courses

    def collect_courses(
        self,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        # Implementation for bulk collection
        campus_code = campus_code or "ssu"
        univ_code = univ_code or "ssu_all"
        faculty_code = faculty_code or "ssu_all"

        courses = self.get_courses(
            year, semester,
            campus_code,
            univ_code,
            faculty_code
        )
        # For SSU, we return a dummy payload or the captured HTML size in a payload dump format
        payload_dump = RawPayloadDump(
            provider="ssu",
            year=year,
            semester=semester,
            campus_code=campus_code,
            university_code=univ_code,
            faculty_code=faculty_code,
            payload=[{"message": "Scraped via Playwright", "course_count": len(courses)}]
        )
        return courses, [payload_dump]

def create_ssu_service(settings: AppSettings) -> SsuService:
    return SsuService(settings)
