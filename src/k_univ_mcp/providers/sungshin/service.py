from __future__ import annotations

from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.sungshin.client import SungshinClient
from k_univ_mcp.providers.sungshin.parser import build_course

class SungshinService:
    def __init__(self, client: SungshinClient | None = None):
        self.client = client or SungshinClient()

    def get_campuses(self, year: str, semester: str):
        from k_univ_mcp.models import Campus
        return [
            Campus(code="COMM060.1", name="수정"),
            Campus(code="COMM060.2", name="운정"),
        ]

    def get_colleges(self, campus_code: str, year: str, semester: str):
        from k_univ_mcp.models import College
        return [
            College(
                campus_code=campus_code,
                code="COMM075.101",
                name="학사과정",
            )
        ]

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        year: str,
        semester: str,
    ):
        from k_univ_mcp.models import Department

        data = self.client.onload()
        dept_list = data.get("deptList", [])

        results = []
        for dept in dept_list:
            if dept.get("orgClsfCd") == college_code:
                name = dept.get("cmnCdNm", "")
                if name.startswith("[대학]"):
                    name = name[4:]

                results.append(
                    Department(
                        campus_code=campus_code,
                        college_code=college_code,
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
        college_code: str,
        department_code: str,
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
            org_clsf_code=college_code,
            dpt_mjr_code=department_code,
        )

        return [
            build_course(row, year=year, semester=sem_cd)
            for row in rows
        ]

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
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

        campuses = [c for c in self.get_campuses(year, semester) if campus_code in {None, c.code}]
        for campus in campuses:
            colleges = [u for u in self.get_colleges(campus.code, year, semester) if college_code in {None, u.code}]
            for college in colleges:
                departments = [f for f in self.get_departments(campus.code, college.code, year, semester) if department_code in {None, f.code}]
                for department in departments:
                    rows = self.client.fetch_courses(
                        year=year,
                        semester=sem_cd,
                        cmp_code=campus.code,
                        org_clsf_code=college.code,
                        dpt_mjr_code=department.code,
                    )
                    raw_payloads.append(
                        RawPayloadDump(
                            provider="sungshin",
                            year=year,
                            semester=sem_cd,
                            campus_code=campus.code,
                            college_code=college.code,
                            department_code=department.code,
                            payload=rows,
                        )
                    )
                    for row in rows:
                        courses.append(build_course(row, year=year, semester=sem_cd))

        return courses, raw_payloads

def create_sungshin_service(settings: Any = None) -> SungshinService:
    from k_univ_mcp.providers.sungshin.client import SungshinClient
    client = SungshinClient(
        timeout=getattr(settings, "sungshin_timeout", 30),
        sleep_seconds=getattr(settings, "sungshin_sleep_seconds", 0.2),
    )
    return SungshinService(client=client)
