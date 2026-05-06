from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from k_univ_mcp.browser_bootstrap import BrowserBootstrapSettings, BrowserBootstrapTarget, BrowserSessionBootstrap
from k_univ_mcp.models import Campus, Course, Department, RawPayloadDump, College
from k_univ_mcp.providers.yonsei.bootstrap import EnvCookieBootstrap
from k_univ_mcp.providers.yonsei.client import YonseiClient, YonseiError
from k_univ_mcp.providers.yonsei.models import YonseiCourseRow, YonseiDepartmentRow
from k_univ_mcp.providers.yonsei.parser import build_course
from k_univ_mcp.semester import normalize_provider_semester
from k_univ_mcp.settings import AppSettings

YONSEI_READY_SELECTOR = '[data-ndid="93"][role="button"]'
YONSEI_CLICK_SELECTOR = '[data-ndid="93"][role="button"]'
YONSEI_REQUIRED_BROWSER_COOKIES = ("JSESSIONID",)

YONSEI_CAMPUSES: dict[str, tuple[str, str]] = {
    "sinchon-undergraduate": ("s1", "연세대학교 신촌캠퍼스 학부"),
    "mirae-undergraduate": ("s2", "연세대학교 미래캠퍼스 학부"),
    "sinchon-graduate": ("s3", "연세대학교 신촌캠퍼스 대학원"),
    "mirae-graduate": ("s4", "연세대학교 미래캠퍼스 대학원"),
    "sinchon-medical": ("s7", "연세대학교 신촌캠퍼스 의료원"),
    "mirae-medical": ("s8", "연세대학교 미래캠퍼스 의료원"),
}

YONSEI_UPSTREAM_TO_PUBLIC_CAMPUS: dict[str, str] = {
    upstream_code: public_code for public_code, (upstream_code, _) in YONSEI_CAMPUSES.items()
}


@dataclass(slots=True)
class YonseiSeedCatalog:
    seed_root: Path | None = None

    def _load(self, file_name: str) -> dict[str, Any]:
        if self.seed_root:
            path = self.seed_root / file_name
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        package_root = resources.files("k_univ_mcp.providers.yonsei.data")
        return json.loads(package_root.joinpath(file_name).read_text(encoding="utf-8"))

    def campuses(self) -> list[YonseiDepartmentRow]:
        payload = self._load("campuses.json")
        return [YonseiDepartmentRow.from_payload(item) for item in payload.get("dsCampsBusnsCd", [])]

    def colleges(self, campus_code: str) -> list[YonseiDepartmentRow]:
        file_name = f"universities_{campus_code}.json"
        try:
            payload = self._load(file_name)
        except FileNotFoundError:
            return []
        return [YonseiDepartmentRow.from_payload(item) for item in payload.get("dsUnivCd", [])]


@dataclass(slots=True)
class YonseiService:
    client: YonseiClient | Any | None
    seed_catalog: YonseiSeedCatalog

    def _require_client(self) -> YonseiClient | Any:
        if self.client is None:
            raise ValueError(
                "Yonsei live API access requires YONSEI_COOKIE. Seeded campus and college discovery can work without it."
            )
        return self.client

    @staticmethod
    def _require_term(year: str, semester: str) -> tuple[str, str]:
        if not year or not semester:
            raise ValueError("Year and semester are required and must be passed explicitly.")
        return year, normalize_provider_semester("yonsei", semester)

    @staticmethod
    def _public_campus_code(campus_code: str) -> str:
        return YONSEI_UPSTREAM_TO_PUBLIC_CAMPUS.get(campus_code, campus_code)

    @classmethod
    def _resolve_upstream_campus_code(cls, campus_code: str) -> str:
        if campus_code in YONSEI_CAMPUSES:
            return YONSEI_CAMPUSES[campus_code][0]
        if campus_code in YONSEI_UPSTREAM_TO_PUBLIC_CAMPUS:
            return campus_code
        raise ValueError(f"Unsupported Yonsei campus code: {campus_code}")

    @classmethod
    def _campus_name(cls, campus_code: str, fallback: str | None = None) -> str:
        public_code = cls._public_campus_code(campus_code)
        campus_info = YONSEI_CAMPUSES.get(public_code)
        if campus_info is not None:
            return campus_info[1]
        return fallback or public_code

    @classmethod
    def _to_campuses(cls, rows: list[YonseiDepartmentRow]) -> list[Campus]:
        return [
            Campus(
                code=cls._public_campus_code(row.code),
                name=cls._campus_name(row.code, row.name),
                english_name=row.english_name,
                raw=row.raw,
            )
            for row in rows
        ]

    @staticmethod
    def _to_universities(campus_code: str, rows: list[YonseiDepartmentRow]) -> list[College]:
        return [
            College(
                campus_code=campus_code,
                code=row.code,
                name=row.name,
                english_name=row.english_name,
                raw=row.raw,
            )
            for row in rows
        ]

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        resolved_year, resolved_semester = self._require_term(year, semester)
        if self.client is None:
            return self._to_campuses(self.seed_catalog.campuses())

        return self._to_campuses(
            [YonseiDepartmentRow.from_payload(item) for item in self.client.list_campuses(resolved_year, resolved_semester)]
        )

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]:
        resolved_year, resolved_semester = self._require_term(year, semester)
        public_campus_code = self._public_campus_code(campus_code)
        upstream_campus_code = self._resolve_upstream_campus_code(campus_code)
        if self.client is None:
            return self._to_universities(public_campus_code, self.seed_catalog.colleges(upstream_campus_code))

        return self._to_universities(
            public_campus_code,
            [
                YonseiDepartmentRow.from_payload(item)
                for item in self.client.list_universities(resolved_year, resolved_semester, upstream_campus_code)
            ],
        )

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]:
        resolved_year, resolved_semester = self._require_term(year, semester)
        public_campus_code = self._public_campus_code(campus_code)
        upstream_campus_code = self._resolve_upstream_campus_code(campus_code)
        departments = self._require_client().list_faculties(
            resolved_year,
            resolved_semester,
            upstream_campus_code,
            college_code,
        )
        return [
            Department(
                campus_code=public_campus_code,
                college_code=college_code,
                code=row.code,
                name=row.name,
                english_name=row.english_name,
                raw=row.raw,
            )
            for row in (YonseiDepartmentRow.from_payload(item) for item in departments)
        ]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[Course]:
        resolved_year, resolved_semester = self._require_term(year, semester)
        public_campus_code = self._public_campus_code(campus_code)
        upstream_campus_code = self._resolve_upstream_campus_code(campus_code)
        campus_name = next(
            (
                campus.name
                for campus in self.get_campuses(year=resolved_year, semester=resolved_semester)
                if campus.code == public_campus_code
            ),
            None,
        )
        college_name = next(
            (
                univ.name
                for univ in self.get_colleges(public_campus_code, year=resolved_year, semester=resolved_semester)
                if univ.code == college_code
            ),
            None,
        )
        department_name = next(
            (
                department.name
                for department in self.get_departments(
                    public_campus_code,
                    college_code,
                    year=resolved_year,
                    semester=resolved_semester,
                )
                if department.code == department_code
            ),
            None,
        )
        return [
            build_course(
                YonseiCourseRow(item),
                year=resolved_year,
                semester=resolved_semester,
                campus_code=public_campus_code,
                campus_name=campus_name,
                college_code=college_code,
                college_name=college_name,
                department_code=department_code,
                department_name=department_name,
            )
            for item in self._require_client().list_courses(
                resolved_year,
                resolved_semester,
                upstream_campus_code,
                college_code,
                department_code,
            )
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
        resolved_public_campus_code = self._public_campus_code(campus_code) if campus_code is not None else None
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        campuses = [
            campus
            for campus in self.get_campuses(year=resolved_year, semester=resolved_semester)
            if resolved_public_campus_code in {None, campus.code}
        ]
        for campus in campuses:
            colleges = [
                univ
                for univ in self.get_colleges(campus.code, year=resolved_year, semester=resolved_semester)
                if college_code in {None, univ.code}
            ]
            for college in colleges:
                departments = [
                    department
                    for department in self.get_departments(
                        campus.code,
                        college.code,
                        year=resolved_year,
                        semester=resolved_semester,
                    )
                    if department_code in {None, department.code}
                ]
                for department in departments:
                    upstream_campus_code = self._resolve_upstream_campus_code(campus.code)
                    payload = self._require_client().list_courses(
                        resolved_year,
                        resolved_semester,
                        upstream_campus_code,
                        college.code,
                        department.code,
                    )
                    raw_payloads.append(
                        RawPayloadDump(
                            provider="yonsei",
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
                                YonseiCourseRow(item),
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


def create_yonsei_service(settings: AppSettings | None = None) -> YonseiService:
    app_settings = settings or AppSettings.from_env()
    browser_bootstrap = None
    refresh_cookie_header = None
    if app_settings.enable_browser_bootstrap:
        browser_bootstrap = BrowserSessionBootstrap(
            target=BrowserBootstrapTarget(
                entry_url=app_settings.yonsei_referer,
                required_cookie_names=YONSEI_REQUIRED_BROWSER_COOKIES,
                ready_selector=YONSEI_READY_SELECTOR,
                click_selector=YONSEI_CLICK_SELECTOR,
            ),
            settings=BrowserBootstrapSettings(
                enabled=True,
                browser=app_settings.browser,
                timeout_ms=app_settings.browser_bootstrap_timeout_ms,
                ready_selector_override=app_settings.browser_ready_selector,
                click_selector_override=app_settings.browser_click_selector,
                auto_install_browser=app_settings.auto_install_playwright_browser,
            ),
        )
        refresh_cookie_header = browser_bootstrap.resolve_cookie_header

    client = None
    cookie_header = None
    if app_settings.yonsei_cookie:
        cookie_header = EnvCookieBootstrap(app_settings.yonsei_cookie).resolve_cookie_header()
    elif refresh_cookie_header is not None and app_settings.browser_bootstrap_on_start:
        cookie_header = refresh_cookie_header()
    elif refresh_cookie_header is not None:
        cookie_header = ""

    if cookie_header is not None:
        client = YonseiClient(
            cookie_header=cookie_header,
            referer=app_settings.yonsei_referer,
            timeout=app_settings.yonsei_timeout,
            retry_total=app_settings.yonsei_retry_total,
            retry_backoff=app_settings.yonsei_retry_backoff,
            sleep_seconds=app_settings.yonsei_sleep_seconds,
            session_refresh_retries=app_settings.yonsei_session_refresh_retries,
            refresh_cookie_header=refresh_cookie_header,
        )
    return YonseiService(
        client=client,
        seed_catalog=YonseiSeedCatalog(seed_root=app_settings.yonsei_seed_root),
    )
