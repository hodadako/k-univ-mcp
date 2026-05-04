from __future__ import annotations

from typing import Any

from k_univ_mcp.models import Course, SearchParams
from k_univ_mcp.providers.sungshin.client import SungshinClient
from k_univ_mcp.providers.sungshin.parser import build_course

class SungshinService:
    def __init__(self, client: SungshinClient | None = None):
        self.client = client or SungshinClient()

    def get_campuses(self, year: str, semester: str):
        from k_univ_mcp.models import Campus
        return [
            Campus(code="COMM060.1", name="수정", provider="sungshin"),
            Campus(code="COMM060.2", name="운정", provider="sungshin"),
        ]

    def get_universities(self, campus_code: str, year: str, semester: str):
        from k_univ_mcp.models import University
        return [University(code="COMM075.101", name="학부", provider="sungshin")]

    async def search_courses(
        self,
        params: SearchParams,
        **kwargs: Any,
    ) -> list[Course]:
        year = params.year or "2025"
        semester = params.semester or "10"

        if semester == "1":
            sem_cd = "COMM063.10"
        elif semester == "2":
            sem_cd = "COMM063.20"
        elif "." not in semester:
            sem_cd = f"COMM063.{semester}"
        else:
            sem_cd = semester

        org_clsf_cd = kwargs.get("org_clsf_cd", "COMM075.101")
        sbj_mng_cd = kwargs.get("sbj_mng_cd", "")
        obj_crs_cd = kwargs.get("obj_crs_cd", "USSR001.10")
        dpt_mjr_cd = kwargs.get("dpt_mjr_cd", "")
        sbj_nm = params.query or ""

        import asyncio
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(
            None,
            lambda: self.client.search_courses(
                year=year,
                semester=sem_cd,
                org_clsf_code=org_clsf_cd,
                sbj_mng_code=sbj_mng_cd,
                obj_crs_code=obj_crs_cd,
                dpt_mjr_code=dpt_mjr_cd,
                sbj_no_nm=sbj_nm,
            )
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
