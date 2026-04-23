from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from k_univ_mcp.browser_bootstrap import BrowserBootstrapSettings, BrowserBootstrapTarget, BrowserSessionBootstrap
from k_univ_mcp.models import Campus, Course, Faculty, RawPayloadDump, University
from k_univ_mcp.providers.yonsei.bootstrap import EnvCookieBootstrap
from k_univ_mcp.providers.yonsei.client import YonseiClient, YonseiError
from k_univ_mcp.providers.yonsei.models import YonseiCourseRow, YonseiDepartmentRow
from k_univ_mcp.providers.yonsei.parser import build_course
from k_univ_mcp.settings import AppSettings

YONSEI_READY_SELECTOR = '[data-ndid="93"][role="button"]'
YONSEI_CLICK_SELECTOR = '[data-ndid="93"][role="button"]'
YONSEI_REQUIRED_BROWSER_COOKIES = ("JSESSIONID",)


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

    def universities(self, campus_code: str) -> list[YonseiDepartmentRow]:
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
                "Yonsei live API access requires YONSEI_COOKIE. Seeded campus and university discovery can work without it."
            )
        return self.client

    @staticmethod
    def _require_term(year: str, semester: str) -> tuple[str, str]:
        if not year or not semester:
            raise ValueError("Year and semester are required and must be passed explicitly.")
        return year, semester

    @staticmethod
    def _to_campuses(rows: list[YonseiDepartmentRow]) -> list[Campus]:
        return [Campus(code=row.code, name=row.name, english_name=row.english_name, raw=row.raw) for row in rows]

    @staticmethod
    def _to_universities(campus_code: str, rows: list[YonseiDepartmentRow]) -> list[University]:
        return [
            University(
                campus_code=campus_code,
                code=row.code,
                name=row.name,
                english_name=row.english_name,
                raw=row.raw,
            )
            for row in rows
        ]

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        self._require_term(year, semester)
        if self.client is None:
            return self._to_campuses(self.seed_catalog.campuses())

        return self._to_campuses(
            [YonseiDepartmentRow.from_payload(item) for item in self.client.list_campuses(year, semester)]
        )

    def get_universities(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[University]:
        self._require_term(year, semester)
        if self.client is None:
            return self._to_universities(campus_code, self.seed_catalog.universities(campus_code))

        return self._to_universities(
            campus_code,
            [
                YonseiDepartmentRow.from_payload(item) for item in self.client.list_universities(year, semester, campus_code)
            ],
        )

    def get_faculties(
        self,
        campus_code: str,
        univ_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Faculty]:
        resolved_year, resolved_semester = self._require_term(year, semester)
        faculties = self._require_client().list_faculties(resolved_year, resolved_semester, campus_code, univ_code)
        return [
            Faculty(
                campus_code=campus_code,
                university_code=univ_code,
                code=row.code,
                name=row.name,
                english_name=row.english_name,
                raw=row.raw,
            )
            for row in (YonseiDepartmentRow.from_payload(item) for item in faculties)
        ]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[Course]:
        self._require_term(year, semester)
        campus_name = next(
            (campus.name for campus in self.get_campuses(year=year, semester=semester) if campus.code == campus_code),
            None,
        )
        univ_name = next(
            (
                univ.name
                for univ in self.get_universities(campus_code, year=year, semester=semester)
                if univ.code == univ_code
            ),
            None,
        )
        faculty_name = next(
            (
                faculty.name
                for faculty in self.get_faculties(campus_code, univ_code, year=year, semester=semester)
                if faculty.code == faculty_code
            ),
            None,
        )
        return [
            build_course(
                YonseiCourseRow(item),
                year=year,
                semester=semester,
                campus_code=campus_code,
                campus_name=campus_name,
                university_code=univ_code,
                university_name=univ_name,
                faculty_code=faculty_code,
                faculty_name=faculty_name,
            )
            for item in self._require_client().list_courses(year, semester, campus_code, univ_code, faculty_code)
        ]

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        campuses = [campus for campus in self.get_campuses(year=year, semester=semester) if campus_code in {None, campus.code}]
        for campus in campuses:
            universities = [
                univ
                for univ in self.get_universities(campus.code, year=year, semester=semester)
                if univ_code in {None, univ.code}
            ]
            for university in universities:
                faculties = [
                    faculty
                    for faculty in self.get_faculties(campus.code, university.code, year=year, semester=semester)
                    if faculty_code in {None, faculty.code}
                ]
                for faculty in faculties:
                    payload = self._require_client().list_courses(year, semester, campus.code, university.code, faculty.code)
                    raw_payloads.append(
                        RawPayloadDump(
                            provider="yonsei",
                            year=year,
                            semester=semester,
                            campus_code=campus.code,
                            university_code=university.code,
                            faculty_code=faculty.code,
                            payload=payload,
                        )
                    )
                    for item in payload:
                        courses.append(
                            build_course(
                                YonseiCourseRow(item),
                                year=year,
                                semester=semester,
                                campus_code=campus.code,
                                campus_name=campus.name,
                                university_code=university.code,
                                university_name=university.name,
                                faculty_code=faculty.code,
                                faculty_name=faculty.name,
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
