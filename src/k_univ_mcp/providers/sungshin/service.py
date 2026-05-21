from __future__ import annotations

from typing import Any

from dataclasses import dataclass

from k_univ_mcp.models import Campus, Course, Faculty, RawPayloadDump, University
from k_univ_mcp.providers.sungshin.client import SungshinClient
from k_univ_mcp.providers.sungshin.models import SungshinCourseRow
from k_univ_mcp.providers.sungshin.parser import build_course


@dataclass(slots=True)
class SungshinService:
    client: SungshinClient

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        from k_univ_mcp.models import Campus
        return [
            Campus(code="COMM060.1", name="수정"),
            Campus(code="COMM060.2", name="운정"),
        ]

    def get_universities(self, campus_code: str, *, year: str, semester: str) -> list[University]:
        from k_univ_mcp.models import University
        return [
            University(
                campus_code=campus_code,
                code="COMM075.101",
                name="학사과정",
            )
        ]

    def get_faculties(
        self,
        campus_code: str,
        univ_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Faculty]:
        from k_univ_mcp.models import Faculty

        data = self.client.onload()
        dept_list = data.get("deptList", [])

        results = []
        for dept in dept_list:
            if dept.get("orgClsfCd") == univ_code:
                name = dept.get("cmnCdNm", "")
                if name.startswith("[대학]"):
                    name = name[4:]

                results.append(
                    Faculty(
                        campus_code=campus_code,
                        university_code=univ_code,
                        code=dept.get("cmnCd", ""),
                        name=name,
                    )
                )
        return results

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[Course]:
        if semester == "1":
            sem_cd = "COMM063.10"
        elif semester == "2":
            sem_cd = "COMM063.20"
        elif "." not in semester:
            sem_cd = f"COMM063.{semester}"
        else:
            sem_cd = semester

        rows = self.client.fetch_courses(
            year=year,
            semester=sem_cd,
            cmp_code=campus_code,
            org_clsf_code=univ_code,
            dpt_mjr_code=faculty_code,
        )

        return [
            build_course(SungshinCourseRow(row), year=year, semester=sem_cd)
            for row in rows
        ]

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        if semester == "1":
            sem_cd = "COMM063.10"
        elif semester == "2":
            sem_cd = "COMM063.20"
        elif "." not in semester:
            sem_cd = f"COMM063.{semester}"
        else:
            sem_cd = semester

        campuses = [c for c in self.get_campuses(year=year, semester=semester) if campus_code in {None, c.code}]
        for campus in campuses:
            universities = [
                u
                for u in self.get_universities(campus.code, year=year, semester=semester)
                if univ_code in {None, u.code}
            ]
            for university in universities:
                faculties = [
                    f
                    for f in self.get_faculties(campus.code, university.code, year=year, semester=semester)
                    if faculty_code in {None, f.code}
                ]
                for faculty in faculties:
                    rows = self.client.fetch_courses(
                        year=year,
                        semester=sem_cd,
                        cmp_code=campus.code,
                        org_clsf_code=university.code,
                        dpt_mjr_code=faculty.code,
                    )
                    raw_payloads.append(
                        RawPayloadDump(
                            provider="sungshin",
                            year=year,
                            semester=sem_cd,
                            campus_code=campus.code,
                            university_code=university.code,
                            faculty_code=faculty.code,
                            payload=rows,
                        )
                    )
                    for row in rows:
                        courses.append(build_course(SungshinCourseRow(row), year=year, semester=sem_cd))

        return courses, raw_payloads

def create_sungshin_service(settings: Any = None) -> SungshinService:
    from k_univ_mcp.providers.sungshin.client import SungshinClient
    client = SungshinClient(
        timeout=getattr(settings, "sungshin_timeout", 30),
        sleep_seconds=getattr(settings, "sungshin_sleep_seconds", 0.2),
    )
    return SungshinService(client=client)
