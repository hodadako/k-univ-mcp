from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.hanyang.client import HanyangClient
from k_univ_mcp.providers.hanyang.models import HanyangCourseRow
from k_univ_mcp.providers.hanyang.parser import build_course
from k_univ_mcp.semester import normalize_provider_semester
from k_univ_mcp.settings import AppSettings

HANYANG_CAMPUSES: dict[str, tuple[str, str]] = {
    "seoul": ("H0002256", "한양대학교 서울캠퍼스"),
    "erica": ("H0002263", "한양대학교 ERICA캠퍼스"),
}


@dataclass(slots=True)
class HanyangService:
    client: HanyangClient
    pgm_id: str = "P310278"
    menu_id: str = "M006631"
    tk: str = ""
    page_size: int = 500

    @staticmethod
    def _extract_data_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        for value in payload.values():
            if not isinstance(value, list) or not value:
                continue
            first = value[0]
            if not isinstance(first, dict):
                continue
            data_list = first.get("list", [])
            if isinstance(data_list, list):
                return data_list
        return []

    def _fetch_all_course_rows(
        self,
        *,
        year: str,
        semester: str,
        org_code: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        skip_rows = 0
        total_count: int | None = None

        while True:
            payload = self.client.find_courses(
                year=year,
                semester=semester,
                org_code=org_code,
                pgm_id=self.pgm_id,
                menu_id=self.menu_id,
                tk=self.tk,
                skip_rows=skip_rows,
                max_rows=self.page_size,
            )
            page_rows = self._extract_data_list(payload)
            if not page_rows:
                break

            rows.extend(page_rows)

            if total_count is None:
                raw_total = page_rows[0].get("totalCnt")
                try:
                    total_count = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_count = None

            if total_count is not None and len(rows) >= total_count:
                break
            if len(page_rows) < self.page_size:
                break

            skip_rows += len(page_rows)

        return rows

    @staticmethod
    def _normalize_semester(semester: str) -> str:
        return normalize_provider_semester("hanyang", semester)

    @staticmethod
    def _public_campus_code(campus_code: str) -> str:
        for public_code, (upstream_code, _) in HANYANG_CAMPUSES.items():
            if campus_code in {public_code, upstream_code}:
                return public_code
        raise ValueError(f"Unsupported Hanyang campus code: {campus_code}")

    @classmethod
    def _upstream_campus_code(cls, campus_code: str) -> str:
        return HANYANG_CAMPUSES[cls._public_campus_code(campus_code)][0]

    @classmethod
    def _campus_name(cls, campus_code: str) -> str:
        return HANYANG_CAMPUSES[cls._public_campus_code(campus_code)][1]

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        _ = self._normalize_semester(semester)
        return [
            Campus(code=public_code, name=name, raw={"code": upstream_code})
            for public_code, (upstream_code, name) in HANYANG_CAMPUSES.items()
        ]

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]:
        resolved_semester = self._normalize_semester(semester)
        public_campus_code = self._public_campus_code(campus_code)
        upstream_campus_code = self._upstream_campus_code(campus_code)
        # Attempt to list programs (colleges/departments)
        try:
            payload = self.client.list_programs(
                year=year,
                semester=resolved_semester,
                org_code=upstream_campus_code,
                pgm_id=self.pgm_id,
                menu_id=self.menu_id,
                tk=self.tk,
            )

            # Extract list from payload
            data_list = []
            for key in payload:
                if isinstance(payload[key], list) and len(payload[key]) > 0:
                    data_list = payload[key][0].get("list", [])
                    break

            if not data_list:
                return [
                    College(
                        campus_code=public_campus_code,
                        code=public_campus_code,
                        name="전체",
                        raw={},
                    )
                ]

            # Map pgmNm/pgmCd to College
            # Note: Hanyang's hierarchy is a bit flat in findPgmList
            return [
                College(
                    campus_code=public_campus_code,
                    code=item.get("pgmCd") or public_campus_code,
                    name=item.get("pgmNm") or "전체",
                    raw=item,
                )
                for item in data_list
            ]
        except Exception:
            return [
                College(
                    campus_code=public_campus_code,
                    code=public_campus_code,
                    name="전체",
                    raw={},
                )
            ]

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]:
        public_campus_code = self._public_campus_code(campus_code)
        # Hanyang's hierarchy is relatively flat in the search UI
        return [
            Department(
                campus_code=public_campus_code,
                college_code=college_code,
                code=college_code,
                name="전체",
                raw={"code": college_code},
            )
        ]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[Course]:
        resolved_semester = self._normalize_semester(semester)
        public_campus_code = self._public_campus_code(campus_code)
        rows = self._fetch_all_course_rows(
            year=year,
            semester=resolved_semester,
            org_code=self._upstream_campus_code(campus_code),
        )

        courses = [
            build_course(
                HanyangCourseRow(item),
                year=year,
                semester=resolved_semester,
                campus_code=public_campus_code,
                campus_name=self._campus_name(public_campus_code),
            )
            for item in rows
        ]

        if college_code and college_code != public_campus_code:
            courses = [c for c in courses if c.college_code == college_code]

        if department_code and department_code != public_campus_code:
            courses = [c for c in courses if c.department_code == department_code]

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
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        resolved_public_campus_code = (
            self._public_campus_code(campus_code) if campus_code is not None else None
        )
        campuses = [
            c
            for c in self.get_campuses(year=year, semester=resolved_semester)
            if resolved_public_campus_code in {None, c.code}
        ]
        for campus in campuses:
            data_list = self._fetch_all_course_rows(
                year=year,
                semester=resolved_semester,
                org_code=self._upstream_campus_code(campus.code),
            )

            raw_payloads.append(
                RawPayloadDump(
                    provider="hanyang",
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    college_code=campus.code,
                    department_code=campus.code,
                    payload=data_list,
                )
            )

            for item in data_list:
                course = build_course(
                    HanyangCourseRow(item),
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    campus_name=campus.name,
                )

                # Apply filters if provided
                if (
                    college_code
                    and college_code != campus.code
                    and course.college_code != college_code
                ):
                    continue
                if (
                    department_code
                    and department_code != campus.code
                    and course.department_code != department_code
                ):
                    continue

                courses.append(course)

        return courses, raw_payloads


def create_hanyang_service(settings: AppSettings | None = None) -> HanyangService:
    app_settings = settings or AppSettings.from_env()
    client = HanyangClient(
        cookie_header=app_settings.hanyang_cookie or "",
        timeout=app_settings.hanyang_timeout,
        sleep_seconds=app_settings.hanyang_sleep_seconds,
    )
    return HanyangService(
        client=client,
        pgm_id=app_settings.hanyang_pgm_id,
        menu_id=app_settings.hanyang_menu_id,
        tk=app_settings.hanyang_tk,
    )
