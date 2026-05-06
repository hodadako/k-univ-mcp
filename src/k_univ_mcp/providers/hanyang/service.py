from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.hanyang.client import HanyangClient
from k_univ_mcp.providers.hanyang.models import HanyangCourseRow
from k_univ_mcp.providers.hanyang.parser import build_course
from k_univ_mcp.settings import AppSettings


@dataclass(slots=True)
class HanyangService:
    client: HanyangClient
    pgm_id: str = "P310278"
    menu_id: str = "M006631"
    tk: str = ""

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        # For Hanyang, we'll use seeded campuses for now as discovery is complex
        return [
            Campus(code="H0002256", name="대학(학부/서울)", raw={"code": "H0002256"}),
            Campus(code="H0002263", name="대학(학부/ERICA)", raw={"code": "H0002263"}),
        ]

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]:
        # Attempt to list programs (colleges/departments)
        try:
            payload = self.client.list_programs(
                year=year,
                semester=semester,
                org_code=campus_code,
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
                return [College(campus_code=campus_code, code=campus_code, name="전체", raw={})]

            # Map pgmNm/pgmCd to College
            # Note: Hanyang's hierarchy is a bit flat in findPgmList
            return [
                College(
                    campus_code=campus_code,
                    code=item.get("pgmCd") or campus_code,
                    name=item.get("pgmNm") or "전체",
                    raw=item,
                )
                for item in data_list
            ]
        except Exception:
            return [College(campus_code=campus_code, code=campus_code, name="전체", raw={})]

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]:
        # Hanyang's hierarchy is relatively flat in the search UI
        return [
            Department(
                campus_code=campus_code,
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
        # In Hanyang, we mostly use campus_code (org_code)
        payload = self.client.find_courses(
            year=year,
            semester=semester,
            org_code=campus_code,
            pgm_id=self.pgm_id,
            menu_id=self.menu_id,
            tk=self.tk,
        )

        # Hanyang response structure: {"DS_SUUPGS03TTM01": [{"list": [...]}]}
        rows = []
        for key in payload:
            if isinstance(payload[key], list) and len(payload[key]) > 0:
                data_list = payload[key][0].get("list", [])
                rows.extend(data_list)

        courses = [
            build_course(
                HanyangCourseRow(item),
                year=year,
                semester=semester,
                org_code=campus_code,
            )
            for item in rows
        ]

        if college_code and college_code != campus_code:
            courses = [c for c in courses if c.college_code == college_code]

        if department_code and department_code != campus_code:
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
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        campuses = [c for c in self.get_campuses(year=year, semester=semester) if campus_code in {None, c.code}]
        for campus in campuses:
            payload = self.client.find_courses(
                year=year,
                semester=semester,
                org_code=campus.code,
                pgm_id=self.pgm_id,
                menu_id=self.menu_id,
                tk=self.tk,
            )

            data_list = []
            for key in payload:
                if isinstance(payload[key], list) and len(payload[key]) > 0:
                    data_list = payload[key][0].get("list", [])
                    break

            raw_payloads.append(
                RawPayloadDump(
                    provider="hanyang",
                    year=year,
                    semester=semester,
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
                    semester=semester,
                    org_code=campus.code,
                    org_name=campus.name,
                )

                # Apply filters if provided
                if college_code and college_code != campus.code and course.college_code != college_code:
                    continue
                if department_code and department_code != campus.code and course.department_code != department_code:
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
