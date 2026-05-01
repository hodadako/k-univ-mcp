from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, Course, Faculty, RawPayloadDump, University
from k_univ_mcp.providers.inha.client import InhaClient
from k_univ_mcp.providers.inha.models import InhaCourseRow
from k_univ_mcp.providers.inha.parser import build_course

INHA_CAMPUS_CODE = "yonghyeon"
INHA_CAMPUS_NAME = "인하대학교 용현캠퍼스"


@dataclass(slots=True)
class InhaService:
    client: InhaClient

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        _ = (year, semester)
        return [Campus(code=INHA_CAMPUS_CODE, name=INHA_CAMPUS_NAME)]

    def get_universities(self, campus_code: str, *, year: str, semester: str) -> list[University]:
        if campus_code != INHA_CAMPUS_CODE:
            return []

        # Now using curriculum info to get real universities (colleges)
        depts = self.client.fetch_departments_from_curriculum(year=year)
        if not depts:
            return [University(campus_code=campus_code, code="dept", name="학부(과)")]

        univ_names = sorted(list(set(d["university"] for d in depts)))
        return [
            University(campus_code=campus_code, code=name, name=name)
            for name in univ_names
        ]

    def get_faculties(self, campus_code: str, univ_code: str, *, year: str, semester: str) -> list[Faculty]:
        if campus_code != INHA_CAMPUS_CODE:
            return []

        depts = self.client.fetch_departments_from_curriculum(year=year)
        if not depts:
            # Fallback
            if univ_code == "dept":
                return [
                    Faculty(campus_code=campus_code, university_code=univ_code, code=d["code"], name=d["name"])
                    for d in self.client.fetch_departments()
                ]
            return []

        return [
            Faculty(campus_code=campus_code, university_code=univ_code, code=d["code"], name=d["name"])
            for d in depts if d["university"] == univ_code or univ_code == "dept"
        ]

    def get_courses(self, year: str, semester: str, campus_code: str, univ_code: str, faculty_code: str) -> list[Course]:
        rows = self.client.fetch_courses(faculty_code, year=year, semester=semester)

        # Try to find faculty name
        faculties = self.get_faculties(campus_code, univ_code, year=year, semester=semester)
        faculty_name = next((f.name for f in faculties if f.code == faculty_code), faculty_code)

        courses: list[Course] = []
        for r in rows:
            row_obj = InhaCourseRow(
                haksu_section=str(r["haksu_section"]),
                title=str(r["title"]),
                grade=str(r["grade"]),
                credits=str(r["credits"]),
                category=str(r["category"]),
                time_location=str(r["time_location"]),
                professor=str(r["professor"]),
                evaluation=str(r["evaluation"]),
                note=str(r["note"]),
                raw=r
            )
            courses.append(build_course(
                row_obj,
                year=year,
                semester=semester,
                campus_code=campus_code,
                campus_name=INHA_CAMPUS_NAME,
                university_code=univ_code,
                university_name=univ_code if univ_code != "dept" else "학부(과)",
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
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        if faculty_code:
            res = self.get_courses(year, semester, campus_code or INHA_CAMPUS_CODE, univ_code or "dept", faculty_code)
            return res, []

        all_courses: list[Course] = []
        if univ_code and univ_code != "dept":
            faculties = self.get_faculties(INHA_CAMPUS_CODE, univ_code, year=year, semester=semester)
        else:
            # get all depts regardless of university
            faculties = self.get_faculties(INHA_CAMPUS_CODE, "dept", year=year, semester=semester)

        for f in faculties:
            all_courses.extend(self.get_courses(year, semester, INHA_CAMPUS_CODE, f.university_code, f.code))

        return all_courses, []


def create_inha_service() -> InhaService:
    return InhaService(client=InhaClient())
