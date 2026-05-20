from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, College, Course, Department, RawPayloadDump
from k_univ_mcp.providers.myongji.client import MyongjiClient
from k_univ_mcp.providers.myongji.parser import parse_pdf, build_course
from k_univ_mcp.semester import normalize_provider_semester
from k_univ_mcp.settings import AppSettings

@dataclass(slots=True)
class MyongjiService:
    client: MyongjiClient

    @staticmethod
    def _normalize_semester(semester: str) -> str:
        return normalize_provider_semester("myongji", semester)

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        _ = self._normalize_semester(semester)
        return [
            Campus(code="inmun", name="인문캠퍼스"),
            Campus(code="jayeon", name="자연캠퍼스"),
        ]

    def get_colleges(self, campus_code: str, *, year: str, semester: str) -> list[College]:
        # Since we are PDF-based, we don't have an easy way to list colleges
        # without parsing the entire PDF first.
        # Returning a dummy or a list extracted from static knowledge or past runs.
        return [College(campus_code=campus_code, code="all", name="전체")]

    def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str) -> list[Department]:
        return [Department(campus_code=campus_code, college_code=college_code, code="all", name="전체")]

    def get_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str) -> list[Course]:
        resolved_semester = self._normalize_semester(semester)
        if resolved_semester == "2":
            # Per task requirement, 2nd semester is not supported.
            return []

        article_id = self.client.find_article_id(year, resolved_semester)
        if not article_id:
            return []

        pdf_url = self.client.get_pdf_download_url(article_id)
        if not pdf_url:
            return []

        pdf_bytes = self.client.download_pdf(pdf_url)
        rows = parse_pdf(pdf_bytes)

        courses = [
            build_course(row, year=year, semester=resolved_semester)
            for row in rows
        ]

        # Filter by campus if specified
        if campus_code:
            courses = [c for c in courses if c.campus_code == campus_code]

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
        resolved_semester = self._normalize_semester(semester)
        if resolved_semester == "2":
            return [], []

        article_id = self.client.find_article_id(year, resolved_semester)
        if not article_id:
            return [], []

        pdf_url = self.client.get_pdf_download_url(article_id)
        if not pdf_url:
            return [], []

        pdf_bytes = self.client.download_pdf(pdf_url)
        rows = parse_pdf(pdf_bytes)

        courses = [
            build_course(row, year=year, semester=resolved_semester)
            for row in rows
        ]

        if campus_code:
            courses = [c for c in courses if c.campus_code == campus_code]

        # For Myongji, we treat the whole PDF as one payload dump
        raw_payloads = [
            RawPayloadDump(
                provider="myongji",
                year=year,
                semester=resolved_semester,
                campus_code=campus_code or "all",
                college_code=college_code or "all",
                department_code=department_code or "all",
                payload=[r.raw for r in rows if r.raw]
            )
        ]

        return courses, raw_payloads

def create_myongji_service(settings: AppSettings | None = None) -> MyongjiService:
    app_settings = settings or AppSettings.from_env()
    client = MyongjiClient(
        timeout=app_settings.myongji_timeout if hasattr(app_settings, "myongji_timeout") else 30,
        sleep_seconds=app_settings.myongji_sleep_seconds if hasattr(app_settings, "myongji_sleep_seconds") else 0.5,
    )
    return MyongjiService(client=client)
