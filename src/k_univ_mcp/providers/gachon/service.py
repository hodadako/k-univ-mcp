from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.gachon.client import GachonClient
from k_univ_mcp.providers.gachon.models import GachonCourseRow, GachonDepartmentRow
from k_univ_mcp.providers.gachon.parser import build_course
from k_univ_mcp.settings import AppSettings

GACHON_GLOBAL_CAMPUS_CODE = "gachon-global"
GACHON_MEDICAL_CAMPUS_CODE = "gachon-medical"

GACHON_CAMPUSES: dict[str, tuple[str, str]] = {
    GACHON_GLOBAL_CAMPUS_CODE: ("가천대학교 글로벌캠퍼스", "20"),
    GACHON_MEDICAL_CAMPUS_CODE: ("가천대학교 메디컬캠퍼스", "21"),
}


@dataclass(slots=True)
class GachonService:
    client: GachonClient | Any
    _initial_cache: dict[tuple[str, str, str], tuple[list[dict[str, Any]], list[dict[str, Any]]]] = field(default_factory=dict, repr=False)

    @staticmethod
    def _require_term(year: str, semester: str) -> tuple[str, str]:
        if not year or not semester:
            raise ValueError("Year and semester are required and must be passed explicitly.")
        return year, semester

    @staticmethod
    def _require_campus(campus_code: str) -> None:
        if campus_code not in GACHON_CAMPUSES:
            raise ValueError(f"Unsupported Gachon campus code: {campus_code}")

    @staticmethod
    def _campus_name(campus_code: str) -> str:
        return GACHON_CAMPUSES[campus_code][0]

    @staticmethod
    def _group_type(campus_code: str) -> str:
        return GACHON_CAMPUSES[campus_code][1]

    def _initial(self, campus_code: str, year: str, semester: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        key = (campus_code, year, semester)
        cached = self._initial_cache.get(key)
        if cached is not None:
            return cached
        payload = self.client.list_universities(self._group_type(campus_code))
        self._initial_cache[key] = payload
        return payload

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        self._require_term(year, semester)
        return [Campus(code=code, name=name, raw={"provider": "gachon", "groupType": group_type}) for code, (name, group_type) in GACHON_CAMPUSES.items()]

    def get_colleges(self, campus_code: str, *, year: str, semester: str) -> list[College]:
        self._require_term(year, semester)
        self._require_campus(campus_code)
        _, colleges = self._initial(campus_code, year, semester)
        return [
            College(
                campus_code=campus_code,
                code=row.code,
                name=row.name,
                raw=row.raw,
            )
            for row in (GachonDepartmentRow.from_payload(item) for item in colleges)
        ]

    def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str) -> list[Department]:
        self._require_term(year, semester)
        self._require_campus(campus_code)
        return [
            Department(
                campus_code=campus_code,
                college_code=college_code,
                code=row.code,
                name=row.name,
                raw=row.raw,
            )
            for row in (GachonDepartmentRow.from_payload(item) for item in self.client.list_faculties(year, semester, self._group_type(campus_code), college_code))
        ]

    def get_courses(self, year: str, semester: str, campus_code: str, college_code: str, department_code: str) -> list[Course]:
        self._require_term(year, semester)
        self._require_campus(campus_code)
        college_name = next((item.name for item in self.get_colleges(campus_code, year=year, semester=semester) if item.code == college_code), None)
        department_name = next((item.name for item in self.get_departments(campus_code, college_code, year=year, semester=semester) if item.code == department_code), None)
        return [
            build_course(
                GachonCourseRow(item),
                year=year,
                semester=semester,
                campus_code=campus_code,
                campus_name=self._campus_name(campus_code),
                college_code=college_code,
                college_name=college_name,
                department_code=department_code,
                department_name=department_name,
            )
            for item in self.client.list_courses(year, semester, self._group_type(campus_code), college_code, department_code)
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
        resolved_year, resolved_semester = self._require_term(year, semester)
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        campuses = [campus for campus in self.get_campuses(year=resolved_year, semester=resolved_semester) if campus_code in {None, campus.code}]
        for campus in campuses:
            for college in [item for item in self.get_colleges(campus.code, year=resolved_year, semester=resolved_semester) if college_code in {None, item.code}]:
                departments = [
                    item
                    for item in self.get_departments(campus.code, college.code, year=resolved_year, semester=resolved_semester)
                    if department_code in {None, item.code}
                ]
                for department in departments:
                    payload = self.client.list_courses(resolved_year, resolved_semester, self._group_type(campus.code), college.code, department.code)
                    raw_payloads.append(
                        RawPayloadDump(
                            provider="gachon",
                            year=resolved_year,
                            semester=resolved_semester,
                            campus_code=campus.code,
                            college_code=college.code,
                            department_code=department.code,
                            payload=payload,
                        )
                    )
                    for item in payload:
                        courses.append(
                            build_course(
                                GachonCourseRow(item),
                                year=resolved_year,
                                semester=resolved_semester,
                                campus_code=campus.code,
                                campus_name=campus.name,
                                college_code=college.code,
                                college_name=college.name,
                                department_code=department.code,
                                department_name=department.name,
                            )
                        )
        return courses, raw_payloads


def create_gachon_service(settings: AppSettings | None = None) -> GachonService:
    app_settings = settings or AppSettings.from_env()
    client = GachonClient(
        cookie_header=app_settings.gachon_cookie,
        timeout=app_settings.gachon_timeout,
        retry_total=app_settings.gachon_retry_total,
        retry_backoff=app_settings.gachon_retry_backoff,
        sleep_seconds=app_settings.gachon_sleep_seconds,
        user_agent=app_settings.gachon_user_agent,
    )
    return GachonService(client=client)
