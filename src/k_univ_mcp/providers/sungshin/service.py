from __future__ import annotations

from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.sungshin.client import SungshinClient
from k_univ_mcp.providers.sungshin.parser import build_course
from k_univ_mcp.semester import normalize_provider_semester

SUNGSHIN_CAMPUSES: dict[str, tuple[str, str]] = {
    "sujeong": ("COMM060.1", "수정캠퍼스"),
    "unjeong": ("COMM060.2", "운정캠퍼스"),
}


def _resolve_sungshin_semester(semester: str) -> str:
    sem_cd = normalize_provider_semester("sungshin", semester)
    if "." in sem_cd:
        return sem_cd
    return f"COMM063.{sem_cd}"

class SungshinService:
    def __init__(self, client: SungshinClient | None = None):
        self.client = client or SungshinClient()

    @staticmethod
    def _public_campus_code(campus_code: str) -> str:
        for public_code, (upstream_code, _) in SUNGSHIN_CAMPUSES.items():
            if campus_code in {public_code, upstream_code}:
                return public_code
        raise ValueError(f"Unsupported Sungshin campus code: {campus_code}")

    @classmethod
    def _upstream_campus_code(cls, campus_code: str) -> str:
        return SUNGSHIN_CAMPUSES[cls._public_campus_code(campus_code)][0]

    @classmethod
    def _campus_name(cls, campus_code: str) -> str:
        return SUNGSHIN_CAMPUSES[cls._public_campus_code(campus_code)][1]

    def get_campuses(self, year: str, semester: str):
        from k_univ_mcp.models import Campus
        return [
            Campus(code=public_code, name=name, raw={"cmpCd": upstream_code})
            for public_code, (upstream_code, name) in SUNGSHIN_CAMPUSES.items()
        ]

    def get_colleges(self, campus_code: str, year: str, semester: str):
        from k_univ_mcp.models import College
        public_campus_code = self._public_campus_code(campus_code)
        return [
            College(
                campus_code=public_campus_code,
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
        public_campus_code = self._public_campus_code(campus_code)

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
                        campus_code=public_campus_code,
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
        sem_cd = _resolve_sungshin_semester(semester)
        public_campus_code = self._public_campus_code(campus_code)

        rows = self.client.fetch_courses(
            year=year,
            semester=sem_cd,
            cmp_code=self._upstream_campus_code(campus_code),
            org_clsf_code=college_code,
            dpt_mjr_code=department_code,
        )

        return [
            build_course(
                row,
                year=year,
                semester=sem_cd,
                campus_code=public_campus_code,
                campus_name=self._campus_name(public_campus_code),
            )
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

        sem_cd = _resolve_sungshin_semester(semester)
        resolved_public_campus_code = self._public_campus_code(campus_code) if campus_code is not None else None

        campuses = [c for c in self.get_campuses(year, semester) if resolved_public_campus_code in {None, c.code}]
        for campus in campuses:
            colleges = [u for u in self.get_colleges(campus.code, year, semester) if college_code in {None, u.code}]
            for college in colleges:
                departments = [f for f in self.get_departments(campus.code, college.code, year, semester) if department_code in {None, f.code}]
                for department in departments:
                    rows = self.client.fetch_courses(
                        year=year,
                        semester=sem_cd,
                        cmp_code=self._upstream_campus_code(campus.code),
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
                        courses.append(
                            build_course(
                                row,
                                year=year,
                                semester=sem_cd,
                                campus_code=campus.code,
                                campus_name=campus.name,
                            )
                        )

        return courses, raw_payloads

def create_sungshin_service(settings: Any = None) -> SungshinService:
    from k_univ_mcp.providers.sungshin.client import SungshinClient
    client = SungshinClient(
        timeout=getattr(settings, "sungshin_timeout", 30),
        sleep_seconds=getattr(settings, "sungshin_sleep_seconds", 0.2),
    )
    return SungshinService(client=client)
