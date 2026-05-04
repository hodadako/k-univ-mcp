from __future__ import annotations

from typing import Any

from k_univ_mcp.models import Course
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

    def get_universities(self, campus_code: str, year: str, semester: str):
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
        university_code: str,
        year: str,
        semester: str,
    ):
        from k_univ_mcp.models import Faculty

        data = self.client.onload()
        dept_list = data.get("deptList", [])

        results = []
        for dept in dept_list:
            if dept.get("orgClsfCd") == university_code:
                name = dept.get("cmnCdNm", "")
                if name.startswith("[대학]"):
                    name = name[4:]

                results.append(
                    Faculty(
                        campus_code=campus_code,
                        university_code=university_code,
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
        university_code: str,
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
            org_clsf_code=university_code,
            dpt_mjr_code=faculty_code,
        )

        return [
            build_course(row, year=year, semester=sem_cd)
            for row in rows
        ]

def create_sungshin_service(settings: Any = None) -> SungshinService:
    from k_univ_mcp.providers.sungshin.client import SungshinClient
    client = SungshinClient(
        timeout=getattr(settings, "sungshin_timeout", 30),
        sleep_seconds=getattr(settings, "sungshin_sleep_seconds", 0.2),
    )
    return SungshinService(client=client)
