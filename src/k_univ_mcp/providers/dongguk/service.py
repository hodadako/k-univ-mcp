from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from k_univ_mcp.browser_bootstrap import BrowserBootstrapSettings, BrowserBootstrapTarget
from k_univ_mcp.exporter import export_course_batches, merge_exported_batches
from k_univ_mcp.models import Campus, Course, Faculty, RawPayloadDump, University
from k_univ_mcp.providers.dongguk.bootstrap import DONGGUK_REQUIRED_BROWSER_COOKIES, DonggukBrowserBootstrap
from k_univ_mcp.providers.dongguk.client import DonggukClient
from k_univ_mcp.providers.dongguk.models import DonggukCourseRow, DonggukDepartmentRow
from k_univ_mcp.providers.dongguk.parser import build_course, semester_label
from k_univ_mcp.settings import AppSettings


@dataclass(frozen=True, slots=True)
class DonggukCampusAdapter:
    code: str
    name: str
    base_url: str
    index_path: str
    campus_fg: str
    orgn_clsf_cd: str
    conn_orgn_cd: str

    @property
    def referer(self) -> str:
        return f"{self.base_url}{self.index_path}"


DONGGUK_CAMPUS_ADAPTERS: dict[str, DonggukCampusAdapter] = {
    "CM030.10": DonggukCampusAdapter(
        code="CM030.10",
        name="서울",
        base_url="https://support.dongguk.edu",
        index_path="/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039",
        campus_fg="S",
        orgn_clsf_cd="CM015.110",
        conn_orgn_cd="DS03",
    ),
    "CM030.21": DonggukCampusAdapter(
        code="CM030.21",
        name="WISE",
        base_url="https://support.dongguk.ac.kr",
        index_path="/unis/index.do?t=654867724D6E564B57577777554374315558647861564273646A524251543039",
        campus_fg="K",
        orgn_clsf_cd="CM015.230",
        conn_orgn_cd="DK",
    ),
}


def require_dongguk_export_batch_size(batch_size: int | None) -> int:
    if batch_size is None or batch_size <= 0:
        raise ValueError("Dongguk export requires a positive batch_size to avoid long-running MCP timeouts.")
    return batch_size


def export_dongguk_courses(
    service: "DonggukService",
    *,
    year: str,
    semester: str,
    outdir: Path,
    campus_code: str | None = None,
    univ_code: str | None = None,
    faculty_code: str | None = None,
    batch_index: int | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    resolved_batch_size = require_dongguk_export_batch_size(batch_size)
    stem = f"dongguk_{year}_{semester}"
    total_targets = service.count_course_targets(
        year=year,
        semester=semester,
        campus_code=campus_code,
        univ_code=univ_code,
        faculty_code=faculty_code,
    )
    total_batches = service.batch_count(total_targets, resolved_batch_size)

    if batch_index is not None:
        artifacts, row_count = export_course_batches(
            service.iter_course_batches(
                year=year,
                semester=semester,
                campus_code=campus_code,
                univ_code=univ_code,
                faculty_code=faculty_code,
                batch_index=batch_index,
                batch_size=resolved_batch_size,
            ),
            outdir,
            stem,
        )
        next_batch_index = batch_index + 1 if batch_index + 1 < total_batches else None
        return {
            "artifacts": artifacts,
            "row_count": row_count,
            "total_targets": total_targets,
            "batch_index": batch_index,
            "batch_size": resolved_batch_size,
            "total_batches": total_batches,
            "next_batch_index": next_batch_index,
        }

    batch_results: list[dict[str, Any]] = []
    batch_dirs: list[Path] = []
    for current_batch_index in range(total_batches):
        batch_outdir = outdir / f"batch-{current_batch_index}"
        artifacts, row_count = export_course_batches(
            service.iter_course_batches(
                year=year,
                semester=semester,
                campus_code=campus_code,
                univ_code=univ_code,
                faculty_code=faculty_code,
                batch_index=current_batch_index,
                batch_size=resolved_batch_size,
            ),
            batch_outdir,
            stem,
        )
        batch_dirs.append(batch_outdir)
        batch_results.append(
            {
                "batch_index": current_batch_index,
                "row_count": row_count,
                "artifacts": artifacts,
            }
        )

    merged_artifacts, merged_row_count = merge_exported_batches(batch_dirs, outdir, stem)
    return {
        "artifacts": merged_artifacts,
        "row_count": merged_row_count,
        "total_targets": total_targets,
        "batch_index": None,
        "batch_size": resolved_batch_size,
        "total_batches": total_batches,
        "next_batch_index": None,
        "batch_results": batch_results,
    }


def _iter_dicts(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, dict):
        rows.append(value)
        for nested in value.values():
            rows.extend(_iter_dicts(nested))
    elif isinstance(value, list):
        for item in value:
            rows.extend(_iter_dicts(item))
    return rows


def _strip_prefix(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if cleaned.startswith("[") and "]" in cleaned:
        cleaned = cleaned.split("]", 1)[1].strip()
    return cleaned or None


def _campus_name_from_full_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    match = re.search(r"\[([^\]]+)\]", full_name)
    if match:
        return match.group(1).strip() or None
    return _strip_prefix(full_name)


def _pick_name_from_full_name(full_name: str | None, *, take_last: bool = False) -> str | None:
    if not full_name:
        return None
    cleaned = _strip_prefix(full_name) or full_name.strip()
    parts = [part.strip() for part in cleaned.split(">") if part.strip()]
    if not parts:
        return None
    return parts[-1] if take_last else parts[0]


@dataclass(slots=True)
class DonggukCatalog:
    payload: dict[str, Any]
    campuses: list[Campus]
    universities: list[University]
    faculties: list[Faculty]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DonggukCatalog":
        rows = [
            row
            for row in _iter_dicts(payload)
            if any(key in row for key in ("CAMPUS_CD", "CAMPUS_FG", "COLG_CD", "DPT_CD"))
            and any(key in row for key in ("DEPT_NM_FULL", "FULL_NAME", "DEPT_NM", "CAMPUS_NM", "COLG_NM"))
        ]

        campus_map: dict[str, Campus] = {}
        university_map: dict[str, University] = {}
        faculty_map: dict[str, Faculty] = {}

        for row in rows:
            payload_row = DonggukDepartmentRow.from_payload(row)
            campus_code = payload_row.campus_code or payload_row.code
            if campus_code and campus_code not in campus_map:
                campus_name = _campus_name_from_full_name(row.get("CAMPUS_NM_FULL") or row.get("DEPT_NM_FULL") or row.get("FULL_NAME"))
                campus_name = campus_name or _strip_prefix(row.get("CAMPUS_NM")) or payload_row.name or campus_code
                campus_map[campus_code] = Campus(code=campus_code, name=campus_name, english_name=payload_row.english_name, raw=row)

            university_code = payload_row.university_code
            if university_code and university_code not in university_map:
                university_name = _pick_name_from_full_name(
                    row.get("DEPT_NM_FULL") or row.get("FULL_NAME") or row.get("COLG_NM_FULL") or row.get("COLG_NM"),
                    take_last=False,
                ) or _strip_prefix(row.get("COLG_NM") or row.get("DEPT_NM") or payload_row.name)
                university_map[university_code] = University(
                    campus_code=campus_code,
                    code=university_code,
                    name=university_name or payload_row.name,
                    english_name=payload_row.english_name,
                    raw=row,
                )

            if payload_row.level_code == "CM040.30" and str(row.get("USE_YN", "Y")).upper() == "Y":
                faculty_code = payload_row.code
                if faculty_code not in faculty_map:
                    faculty_name = _pick_name_from_full_name(
                        row.get("DEPT_NM_FULL") or row.get("FULL_NAME") or row.get("DEPT_NM"),
                        take_last=True,
                    ) or payload_row.name
                    faculty_map[faculty_code] = Faculty(
                        campus_code=campus_code,
                        university_code=university_code or "",
                        code=faculty_code,
                        name=faculty_name,
                        english_name=payload_row.english_name,
                        raw=row,
                    )

        return cls(
            payload=payload,
            campuses=list(campus_map.values()),
            universities=list(university_map.values()),
            faculties=list(faculty_map.values()),
        )


@dataclass(slots=True)
class DonggukService:
    clients: dict[str, DonggukClient | Any]
    _catalog_cache: dict[tuple[str, str, str], DonggukCatalog] = field(default_factory=dict, repr=False)
    _semester_cache: dict[tuple[str, str, str], str] = field(default_factory=dict, repr=False)

    def _require_client(self, campus_code: str) -> DonggukClient | Any:
        client = self.clients.get(campus_code)
        if client is None:
            raise ValueError(f"Dongguk live API access requires a configured client for campus {campus_code}.")
        return client

    @staticmethod
    def _require_adapter(campus_code: str) -> DonggukCampusAdapter:
        adapter = DONGGUK_CAMPUS_ADAPTERS.get(campus_code)
        if adapter is None:
            raise ValueError(f"Unsupported Dongguk campus code: {campus_code}")
        return adapter

    @staticmethod
    def _require_term(year: str, semester: str) -> tuple[str, str]:
        if not year or not semester:
            raise ValueError("Year and semester are required and must be passed explicitly.")
        return year, semester

    @staticmethod
    def _normalize_term_text(value: str | None) -> str:
        if value is None:
            return ""
        return re.sub(r"\s+", "", str(value).strip()).casefold()

    @staticmethod
    def _extract_term_text(row: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @classmethod
    def _row_matches_year(cls, row: dict[str, Any], year: str) -> bool:
        row_year = cls._extract_term_text(row, "OPEN_YY", "YY", "YEAR")
        return row_year in {None, "", year}

    @classmethod
    def _semester_candidates(cls, row: dict[str, Any]) -> set[str]:
        code = cls._extract_term_text(row, "OPEN_SEM_CD", "SEM_CD")
        label = cls._extract_term_text(row, "OPEN_SEM_NM", "SEM_NM", "CD_NM", "CODE_NM", "NAME", "NM")

        candidates: set[str] = set()

        def add_candidate(value: str | None) -> None:
            normalized = cls._normalize_term_text(value)
            if normalized:
                candidates.add(normalized)

        add_candidate(code)
        add_candidate(label)
        if code:
            resolved_label = semester_label(code)
            add_candidate(resolved_label)
            if resolved_label:
                match = re.search(r"([12])학기", resolved_label)
                if match:
                    add_candidate(match.group(1))
        if label:
            match = re.search(r"([12])학기", label)
            if match:
                add_candidate(match.group(1))

        return candidates

    def _resolve_semester(self, campus_code: str, year: str, semester: str) -> str:
        _ = self._require_term(year, semester)
        _ = self._require_adapter(campus_code)

        cache_key = (campus_code, year, semester)
        cached = self._semester_cache.get(cache_key)
        if cached is not None:
            return cached

        requested = self._normalize_term_text(semester)
        rows = self._require_client(campus_code).fetch_semesters()

        matching_code: str | None = None
        available_codes: list[str] = []
        available_labels: list[str] = []
        seen_codes: set[str] = set()

        for row in rows:
            if not self._row_matches_year(row, year):
                continue
            code = self._extract_term_text(row, "OPEN_SEM_CD", "SEM_CD")
            if not code:
                continue
            if code not in seen_codes:
                seen_codes.add(code)
                available_codes.append(code)
                label = self._extract_term_text(row, "OPEN_SEM_NM", "SEM_NM", "CD_NM", "CODE_NM", "NAME", "NM") or semester_label(code)
                if label:
                    available_labels.append(f"{code} ({label})")
            if requested in self._semester_candidates(row):
                matching_code = code
                break

        if matching_code is None:
            if available_labels:
                available_hint = ", ".join(available_labels)
            elif available_codes:
                available_hint = ", ".join(available_codes)
            else:
                available_hint = "none returned by doLoad.do"
            raise ValueError(
                f"Dongguk semester '{semester}' is not available for {campus_code} in {year}. "
                + f"Available semesters from doLoad.do: {available_hint}"
            )

        self._semester_cache[cache_key] = matching_code
        return matching_code

    def _catalog(self, campus_code: str, year: str, semester: str) -> DonggukCatalog:
        resolved_semester = self._resolve_semester(campus_code, year, semester)
        key = (campus_code, year, resolved_semester)
        catalog = self._catalog_cache.get(key)
        if catalog is not None:
            return catalog
        payload = self._require_client(campus_code).load_course_page()
        if not isinstance(payload, dict):
            raise ValueError("Dongguk doLoad.do must return a JSON object.")
        catalog = DonggukCatalog.from_payload(payload)
        self._catalog_cache[key] = catalog
        return catalog

    @staticmethod
    def _to_campuses(rows: list[Campus]) -> list[Campus]:
        if rows:
            return rows
        return [Campus(code=adapter.code, name=adapter.name, raw={"CAMPUS_CD": adapter.code}) for adapter in DONGGUK_CAMPUS_ADAPTERS.values()]

    @staticmethod
    def _to_universities(campus_code: str, rows: list[University]) -> list[University]:
        return [university for university in rows if university.campus_code in {None, campus_code, ""} or university.campus_code == campus_code]

    @staticmethod
    def _to_faculties(campus_code: str, univ_code: str, rows: list[Faculty]) -> list[Faculty]:
        return [
            faculty
            for faculty in rows
            if (faculty.campus_code in {None, campus_code, ""} or faculty.campus_code == campus_code)
            and (faculty.university_code in {None, univ_code, ""} or faculty.university_code == univ_code)
        ]

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        self._require_term(year, semester)
        return [Campus(code=adapter.code, name=adapter.name, raw={"CAMPUS_CD": adapter.code}) for adapter in DONGGUK_CAMPUS_ADAPTERS.values()]

    def get_universities(self, campus_code: str, *, year: str, semester: str) -> list[University]:
        self._require_term(year, semester)
        self._require_adapter(campus_code)
        return self._to_universities(campus_code, self._catalog(campus_code, year, semester).universities)

    def get_faculties(
        self,
        campus_code: str,
        univ_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Faculty]:
        self._require_term(year, semester)
        self._require_adapter(campus_code)
        return self._to_faculties(campus_code, univ_code, self._catalog(campus_code, year, semester).faculties)

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[Course]:
        self._require_term(year, semester)
        self._require_adapter(campus_code)
        resolved_semester = self._resolve_semester(campus_code, year, semester)
        catalog = self._catalog(campus_code, year, resolved_semester)
        campus_name = next((campus.name for campus in catalog.campuses if campus.code == campus_code), None)
        if campus_name is None:
            campus_name = self._require_adapter(campus_code).name
        university_name = next((university.name for university in catalog.universities if university.code == univ_code), None)
        faculty_name = next((faculty.name for faculty in catalog.faculties if faculty.code == faculty_code), None)
        rows = self._require_client(campus_code).list_courses(year, resolved_semester, campus_code, univ_code, faculty_code)
        return [
            build_course(
                DonggukCourseRow(row),
                year=year,
                semester=resolved_semester,
                campus_code=campus_code,
                campus_name=campus_name,
                university_code=univ_code,
                university_name=university_name,
                faculty_code=faculty_code,
                faculty_name=faculty_name,
            )
            for row in rows
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

        for batch_courses, batch_raw_payloads in self.iter_course_batches(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        ):
            courses.extend(batch_courses)
            raw_payloads.extend(batch_raw_payloads)
        return courses, raw_payloads

    def _course_targets(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> list[tuple[Campus, University, Faculty]]:
        self._require_term(year, semester)

        targets: list[tuple[Campus, University, Faculty]] = []
        campuses = [
            Campus(code=adapter.code, name=adapter.name, raw={"CAMPUS_CD": adapter.code})
            for adapter in DONGGUK_CAMPUS_ADAPTERS.values()
            if campus_code in {None, adapter.code, ""}
        ]
        for campus in campuses:
            resolved_semester = self._resolve_semester(campus.code, year, semester)
            catalog = self._catalog(campus.code, year, resolved_semester)
            universities = [university for university in self._to_universities(campus.code, catalog.universities) if univ_code in {None, university.code, ""}]
            for university in universities:
                faculties = [faculty for faculty in self._to_faculties(campus.code, university.code, catalog.faculties) if faculty_code in {None, faculty.code, ""}]
                for faculty in faculties:
                    targets.append((campus, university, faculty))
        return targets

    def count_course_targets(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> int:
        return len(
            self._course_targets(
                year=year,
                semester=semester,
                campus_code=campus_code,
                univ_code=univ_code,
                faculty_code=faculty_code,
            )
        )

    @staticmethod
    def batch_count(total_targets: int, batch_size: int | None) -> int:
        if batch_size in {None, 0}:
            return 1 if total_targets or batch_size is None else 0
        assert batch_size is not None
        return max(1, math.ceil(total_targets / batch_size))

    def iter_course_batches(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
        batch_index: int | None = None,
        batch_size: int | None = None,
    ):
        targets = self._course_targets(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )

        if batch_size is not None:
            if batch_size <= 0:
                raise ValueError("batch_size must be a positive integer when provided.")
            resolved_batch_index = batch_index or 0
            if resolved_batch_index < 0:
                raise ValueError("batch_index must be zero or greater when provided.")
            start = resolved_batch_index * batch_size
            end = start + batch_size
            targets = targets[start:end]
        elif batch_index not in {None, 0}:
            raise ValueError("batch_index requires batch_size to be provided.")

        for campus, university, faculty in targets:
            resolved_semester = self._resolve_semester(campus.code, year, semester)
            payload = self._require_client(campus.code).list_courses(year, resolved_semester, campus.code, university.code, faculty.code)
            raw_payload = RawPayloadDump(
                provider="dongguk",
                year=year,
                semester=resolved_semester,
                campus_code=campus.code,
                university_code=university.code,
                faculty_code=faculty.code,
                payload=payload,
            )
            batch_courses = [
                build_course(
                    DonggukCourseRow(row),
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    campus_name=campus.name,
                    university_code=university.code,
                    university_name=university.name,
                    faculty_code=faculty.code,
                    faculty_name=faculty.name,
                )
                for row in payload
            ]
            yield batch_courses, [raw_payload]


def create_dongguk_service(settings: AppSettings | None = None) -> DonggukService:
    app_settings = settings or AppSettings.from_env()
    clients: dict[str, DonggukClient] = {}

    for adapter in DONGGUK_CAMPUS_ADAPTERS.values():
        cookie_header = app_settings.dongguk_cookie
        if adapter.code == "CM030.21":
            cookie_header = app_settings.dongguk_wise_cookie or cookie_header
        else:
            cookie_header = app_settings.dongguk_seoul_cookie or cookie_header

        refresh_session_state = None
        if app_settings.dongguk_enable_browser_bootstrap and not cookie_header:
            browser_bootstrap = DonggukBrowserBootstrap(
                target=BrowserBootstrapTarget(
                    entry_url=adapter.referer,
                    required_cookie_names=DONGGUK_REQUIRED_BROWSER_COOKIES,
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
            refresh_session_state = browser_bootstrap.resolve_session_state

        clients[adapter.code] = DonggukClient(
            cookie_header=cookie_header,
            base_url=adapter.base_url,
            index_path=adapter.index_path,
            referer=adapter.referer,
            campus_code=adapter.code,
            campus_fg=adapter.campus_fg,
            orgn_clsf_cd=adapter.orgn_clsf_cd,
            conn_orgn_cd=adapter.conn_orgn_cd,
            timeout=app_settings.dongguk_timeout,
            retry_total=app_settings.dongguk_retry_total,
            retry_backoff=app_settings.dongguk_retry_backoff,
            sleep_seconds=app_settings.dongguk_sleep_seconds,
            session_refresh_retries=app_settings.dongguk_session_refresh_retries,
            user_agent=app_settings.dongguk_user_agent,
            refresh_session_state=refresh_session_state,
        )

    return DonggukService(clients=clients)
