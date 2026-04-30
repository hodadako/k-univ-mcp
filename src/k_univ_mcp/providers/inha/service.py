from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, Course, Faculty, University
from k_univ_mcp.providers.inha.client import InhaClient
from k_univ_mcp.providers.inha.models import InhaCourseRow
from k_univ_mcp.providers.inha.parser import build_course

INHA_CAMPUS_CODE = "yonghyeon"
INHA_CAMPUS_NAME = "인하대학교 용현캠퍼스"

@dataclass(slots=True)
class InhaService:
    client: InhaClient

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        return [Campus(code=INHA_CAMPUS_CODE, name=INHA_CAMPUS_NAME)]

    def get_universities(self, campus_code: str, *, year: str, semester: str) -> list[University]:
        if campus_code != INHA_CAMPUS_CODE:
            return []
        # Inha structure is flat for simplicity here, mapping everything to a single 'dept' university
        return [University(campus_code=campus_code, code="dept", name="학부(과)")]

    def get_faculties(self, campus_code: str, univ_code: str, *, year: str, semester: str) -> list[Faculty]:
        if campus_code != INHA_CAMPUS_CODE or univ_code != "dept":
            return []
        depts = self.client.fetch_departments()
        return [
            Faculty(campus_code=campus_code, university_code=univ_code, code=d["code"], name=d["name"])
            for d in depts
        ]

    def get_courses(self, year: str, semester: str, campus_code: str, univ_code: str, faculty_code: str) -> list[Course]:
        rows = self.client.fetch_courses(faculty_code, year=year, semester=semester)

        # Get faculty name for context
        faculties = self.get_faculties(campus_code, univ_code, year=year, semester=semester)
        faculty_name = next((f.name for f in faculties if f.code == faculty_code), faculty_code)

        courses = []
        for r in rows:
            row_obj = InhaCourseRow(
                haksu_section=r["haksu_section"],
                title=r["title"],
                grade=r["grade"],
                credits=r["credits"],
                category=r["category"],
                time_location=r["time_location"],
                professor=r["professor"],
                evaluation=r["evaluation"],
                note=r["note"],
                raw=r
            )
            courses.append(build_course(
                row_obj,
                year=year,
                semester=semester,
                campus_code=campus_code,
                campus_name=INHA_CAMPUS_NAME,
                university_code=univ_code,
                university_name="학부(과)",
                faculty_code=faculty_code,
                faculty_name=faculty_name
            ))
        return courses

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> tuple[list[Course], list[Any]]:
        # For simplicity, if faculty_code is provided, just get those
        if faculty_code:
            res = self.get_courses(year, semester, campus_code or INHA_CAMPUS_CODE, univ_code or "dept", faculty_code)
            return res, []

        # Otherwise collect all faculties if needed (might be slow)
        all_courses = []
        faculties = self.get_faculties(INHA_CAMPUS_CODE, "dept", year=year, semester=semester)
        for f in faculties:
             all_courses.extend(self.get_courses(year, semester, INHA_CAMPUS_CODE, "dept", f.code))

        return all_courses, []

def create_inha_service() -> InhaService:
    return InhaService(client=InhaClient())
