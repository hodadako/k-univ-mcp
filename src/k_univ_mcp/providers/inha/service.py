from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
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

    def get_colleges(self, campus_code: str, *, year: str, semester: str) -> list[College]:
        if campus_code != INHA_CAMPUS_CODE:
            return []

        # Now using curriculum info to get real colleges (colleges)
        depts = self.client.fetch_departments_from_curriculum(year=year)
        if not depts:
            return [College(campus_code=campus_code, code="dept", name="학부(과)")]

        univ_names = sorted(list(set(d["college"] for d in depts)))
        return [
            College(campus_code=campus_code, code=name, name=name)
            for name in univ_names
        ]

    def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str) -> list[Department]:
        if campus_code != INHA_CAMPUS_CODE:
            return []

        depts = self.client.fetch_departments_from_curriculum(year=year)
        if not depts:
            # Fallback
            if college_code == "dept":
                return [
                    Department(campus_code=campus_code, college_code=college_code, code=d["code"], name=d["name"])
                    for d in self.client.fetch_departments()
                ]
            return []

        return [
            Department(campus_code=campus_code, college_code=college_code, code=d["code"], name=d["name"])
            for d in depts if d["college"] == college_code or college_code == "dept"
        ]

    def get_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str) -> list[Course]:
        rows = self.client.fetch_courses(department_code, year=year, semester=semester)

        # Try to find department name
        departments = self.get_departments(campus_code, college_code, year=year, semester=semester)
        department_name = next((f.name for f in departments if f.code == department_code), department_code)

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
                college_code=college_code,
                college_name=college_code if college_code != "dept" else "학부(과)",
                department_code=department_code,
                department_name=department_name
            ))
        return courses

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        if department_code:
            res = self.get_courses(year, semester, campus_code or INHA_CAMPUS_CODE, college_code or "dept", department_code)
            return res, []

        all_courses: list[Course] = []
        if college_code and college_code != "dept":
            departments = self.get_departments(INHA_CAMPUS_CODE, college_code, year=year, semester=semester)
        else:
            # get all depts regardless of college
            departments = self.get_departments(INHA_CAMPUS_CODE, "dept", year=year, semester=semester)

        for f in departments:
            all_courses.extend(self.get_courses(year, semester, INHA_CAMPUS_CODE, f.college_code, f.code))

        return all_courses, []


def create_inha_service() -> InhaService:
    return InhaService(client=InhaClient())
