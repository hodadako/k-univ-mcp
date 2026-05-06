from __future__ import annotations

from typing import Protocol

from k_univ_mcp.models import Campus, Course, Department, College, RawPayloadDump
from k_univ_mcp.providers.soongsil.client import SoongsilClient
from k_univ_mcp.providers.soongsil.models import SoongsilCatalogEntry
from k_univ_mcp.providers.soongsil.parser import SoongsilParser
from k_univ_mcp.semester import CANONICAL_SEMESTER_LABELS, canonicalize_semester, normalize_provider_semester
from k_univ_mcp.settings import AppSettings


class SoongsilClientProtocol(Protocol):
    def list_catalog(self, year: str, semester: str) -> list[SoongsilCatalogEntry]: ...

    def collect_course_pages(
        self,
        year: str,
        semester: str,
        entries: list[SoongsilCatalogEntry],
    ) -> list[tuple[SoongsilCatalogEntry, str]]: ...


class SoongsilService:
    settings: AppSettings
    client: SoongsilClientProtocol
    parser: SoongsilParser

    def __init__(self, settings: AppSettings, client: SoongsilClientProtocol | None = None, parser: SoongsilParser | None = None):
        self.settings = settings
        self.client = client or SoongsilClient(
            timeout=settings.browser_bootstrap_timeout_ms // 1000,
            browser=settings.browser
        )
        self.parser = parser or SoongsilParser()
        self._catalog_cache: dict[tuple[str, str], list[SoongsilCatalogEntry]] = {}

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        _ = (year, semester)
        return [Campus(code="soongsil", name="숭실대학교", english_name="Soongsil College")]

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]:
        resolved_semester = normalize_provider_semester("soongsil", semester)
        colleges: list[College] = []
        seen: set[str] = set()
        for entry in self._catalog(year, resolved_semester):
            if entry.college_code in seen:
                continue
            seen.add(entry.college_code)
            colleges.append(
                College(
                    campus_code=campus_code,
                    code=entry.college_code,
                    name=entry.college_name,
                )
            )
        return colleges

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]:
        resolved_semester = normalize_provider_semester("soongsil", semester)
        return [
            Department(
                campus_code=campus_code,
                college_code=college_code,
                code=entry.department_code,
                name=entry.department_name,
            )
            for entry in self._catalog(year, resolved_semester)
            if entry.college_code == college_code
        ]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[Course]:
        resolved_semester = normalize_provider_semester("soongsil", semester)
        courses: list[Course] = []
        term_name = self._term_name(year, semester)

        for entry, html in self._collect_course_pages(year, resolved_semester, college_code, department_code):
            rows = self.parser.parse_courses(html)
            for row in rows:
                courses.append(Course(
                    provider="soongsil",
                    year=year,
                    semester=resolved_semester,
                    term_name=term_name,
                    campus_code=campus_code,
                    campus_name="숭실대학교",
                    college_code=entry.college_code,
                    college_name=entry.college_name,
                    department_code=entry.department_code,
                    department_name=entry.department_name,
                    course_code=row.course_number,
                    section=row.section,
                    course_key=f"{entry.department_code}:{row.course_number}-{row.section}",
                    title=row.course_name,
                    title_english=None,
                    professor_name=row.professor,
                    professor_name_english=None,
                    lecture_time_raw=row.time_location,
                    lecture_time_english_raw=None,
                    classroom=None,
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
                    established_department_code=entry.department_code,
                    established_department_name=row.department or entry.department_name,
                    raw=row.raw
                ))
        return courses

    def collect_courses(
        self,
        year: str,
        semester: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        resolved_semester = normalize_provider_semester("soongsil", semester)
        campus_code = campus_code or "soongsil"
        selected_univ_code = college_code or "soongsil_all"
        selected_faculty_code = department_code or "soongsil_all"

        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []
        term_name = self._term_name(year, semester)

        for entry, html in self._collect_course_pages(year, resolved_semester, selected_univ_code, selected_faculty_code):
            rows = self.parser.parse_courses(html)
            for row in rows:
                courses.append(Course(
                    provider="soongsil",
                    year=year,
                    semester=resolved_semester,
                    term_name=term_name,
                    campus_code=campus_code,
                    campus_name="숭실대학교",
                    college_code=entry.college_code,
                    college_name=entry.college_name,
                    department_code=entry.department_code,
                    department_name=entry.department_name,
                    course_code=row.course_number,
                    section=row.section,
                    course_key=f"{entry.department_code}:{row.course_number}-{row.section}",
                    title=row.course_name,
                    title_english=None,
                    professor_name=row.professor,
                    professor_name_english=None,
                    lecture_time_raw=row.time_location,
                    lecture_time_english_raw=None,
                    classroom=None,
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
                    established_department_code=entry.department_code,
                    established_department_name=row.department or entry.department_name,
                    raw=row.raw,
                ))
            raw_payloads.append(
                RawPayloadDump(
                    provider="soongsil",
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus_code,
                    college_code=entry.college_code,
                    department_code=entry.department_code,
                    payload=[{"college": entry.college_name, "department": entry.department_name, "html_length": len(html), "course_count": len(rows)}],
                )
            )

        unique_courses: dict[tuple[str | None, str | None, str | None], Course] = {}
        for course in courses:
            key = (course.department_code, course.course_code, course.section)
            unique_courses[key] = course
        return list(unique_courses.values()), raw_payloads

    def _catalog(self, year: str, semester: str) -> list[SoongsilCatalogEntry]:
        key = (year, semester)
        if key not in self._catalog_cache:
            self._catalog_cache[key] = self.client.list_catalog(year, semester)
        return self._catalog_cache[key]

    def _term_name(self, year: str, semester: str) -> str:
        canonical = canonicalize_semester(semester)
        label = CANONICAL_SEMESTER_LABELS.get(canonical)
        if label is not None:
            return f"{year}학년도 {label}"
        if semester.endswith("학기"):
            return f"{year}학년도 {semester}"
        return f"{year}학년도 {semester}학기"

    def _collect_course_pages(
        self,
        year: str,
        semester: str,
        college_code: str,
        department_code: str,
    ) -> list[tuple[SoongsilCatalogEntry, str]]:
        catalog = self._catalog(year, semester)
        selected = catalog
        if department_code != "soongsil_all":
            selected = [entry for entry in catalog if entry.department_code == department_code]
        elif college_code != "soongsil_all":
            selected = [entry for entry in catalog if entry.college_code == college_code]
        return self.client.collect_course_pages(year, semester, selected)

def create_soongsil_service(settings: AppSettings) -> SoongsilService:
    return SoongsilService(settings)
