from __future__ import annotations

from collections.abc import Mapping
import re

CANONICAL_SEMESTER_LABELS: dict[str, str] = {
    "1": "1학기",
    "2": "2학기",
    "summer": "여름학기",
    "winter": "겨울학기",
}

SEMESTER_ALIASES: dict[str, str] = {
    "1": "1",
    "1학기": "1",
    "10": "1",
    "2": "2",
    "2학기": "2",
    "20": "2",
    "3": "summer",
    "summer": "summer",
    "여름": "summer",
    "여름학기": "summer",
    "15": "summer",
    "4": "winter",
    "winter": "winter",
    "겨울": "winter",
    "겨울학기": "winter",
    "25": "winter",
}

PROVIDER_SEMESTER_MAPS: dict[str, Mapping[str, str]] = {
    "yonsei": {"1": "10", "2": "20", "summer": "15", "winter": "25"},
    "gachon": {"1": "10", "2": "20", "summer": "15", "winter": "25"},
    "inha": {"1": "1", "2": "2"},
    "sungshin": {"1": "COMM063.10", "2": "COMM063.20"},
    "soongsil": CANONICAL_SEMESTER_LABELS,
    "hanyang": {"1": "10", "2": "20", "summer": "15", "winter": "25"},
    "dongguk": CANONICAL_SEMESTER_LABELS,
    "myongji": {"1": "1", "2": "2", "summer": "summer", "winter": "winter"},
}


def _normalize_semester_key(semester: str) -> str:
    return semester.strip().casefold()


def canonicalize_semester(semester: str) -> str:
    normalized = _normalize_semester_key(semester)
    return SEMESTER_ALIASES.get(normalized, semester.strip())


def normalize_provider_semester(provider: str, semester: str) -> str:
    normalized = semester.strip()
    if not normalized:
        return normalized

    canonical = canonicalize_semester(normalized)
    provider_map = PROVIDER_SEMESTER_MAPS.get(provider)
    if provider_map is None:
        return normalized
    if canonical in provider_map:
        return provider_map[canonical]
    if canonical in CANONICAL_SEMESTER_LABELS and canonical == _normalize_semester_key(normalized):
        raise ValueError(f"Provider '{provider}' does not support unified semester '{normalized}'.")
    return normalized


def semester_display_label(semester: str) -> str:
    normalized = semester.strip()
    if not normalized:
        return normalized

    year_prefixed_match = re.fullmatch(r"\d{4}-(1학기|2학기|여름학기|겨울학기)", normalized)
    if year_prefixed_match:
        return year_prefixed_match.group(1)

    academic_year_match = re.fullmatch(r"\d{4}학년도\s*(1학기|2학기|여름학기|겨울학기)", normalized)
    if academic_year_match:
        return academic_year_match.group(1)

    canonical = canonicalize_semester(normalized)
    if canonical in CANONICAL_SEMESTER_LABELS:
        return CANONICAL_SEMESTER_LABELS[canonical]

    for provider_map in PROVIDER_SEMESTER_MAPS.values():
        for canonical_key, provider_code in provider_map.items():
            if provider_code == normalized and canonical_key in CANONICAL_SEMESTER_LABELS:
                return CANONICAL_SEMESTER_LABELS[canonical_key]

    return normalized


def semester_display_name(semester: str, *, year: str | None = None) -> str:
    _ = year
    return semester_display_label(semester)


def semester_help_text() -> str:
    return "Unified semester input: 1, 2, summer, winter (legacy provider codes are still accepted)."
