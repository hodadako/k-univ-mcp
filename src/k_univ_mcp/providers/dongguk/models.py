from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DonggukSeedDataError(ValueError):
    pass


def _first_non_empty(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _split_full_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    cleaned = value.strip()
    if cleaned.startswith("[") and "]" in cleaned:
        cleaned = cleaned.split("]", 1)[1].strip()
    parts = [part.strip() for part in cleaned.split(">") if part.strip()]
    if not parts:
        return None, None
    return parts[0], parts[-1]


@dataclass(slots=True)
class DonggukDepartmentRow:
    code: str
    name: str
    campus_code: str | None
    college_code: str | None
    level_code: str | None
    full_name: str | None
    english_name: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DonggukDepartmentRow":
        code = _first_non_empty(payload, "DPT_CD", "COLG_CD", "CAMPUS_CD", "CAMPUS_FG", "CODE")
        if not code:
            raise DonggukSeedDataError("Dongguk rows must include a department, college, or campus code.")

        raw_full_name = _first_non_empty(payload, "DEPT_NM_FULL", "FULL_NAME", "CAMPUS_NM_FULL", "COLG_NM_FULL")
        prefix_name, suffix_name = _split_full_name(raw_full_name)
        name = _first_non_empty(
            payload,
            "DEPT_NM",
            "CAMPUS_NM",
            "COLG_NM",
            "CAMPUS_NM_KOR",
            "COLG_NM_KOR",
        )
        if not name:
            name = suffix_name or prefix_name
        if not name:
            raise DonggukSeedDataError("Dongguk rows must include a readable name field.")

        return cls(
            code=str(code),
            name=str(name),
            campus_code=_first_non_empty(payload, "CAMPUS_CD", "CAMPUS_FG"),
            college_code=_first_non_empty(payload, "COLG_CD"),
            level_code=_first_non_empty(payload, "DEPT_LVL_CD", "ORGN_CLSF_CD"),
            full_name=raw_full_name,
            english_name=_first_non_empty(payload, "DEPT_NM_ENG", "ENG_NM", "CAMPUS_NM_ENG", "COLG_NM_ENG"),
            raw=payload,
        )


@dataclass(slots=True)
class DonggukCourseRow:
    payload: dict[str, Any]

    @property
    def course_code(self) -> str | None:
        return _first_non_empty(self.payload, "SBJ_NO")

    @property
    def section(self) -> str | None:
        return _first_non_empty(self.payload, "DVCLS")

    @property
    def title(self) -> str | None:
        return _first_non_empty(self.payload, "SBJ_NM", "SBJ_NM_KOR")

    @property
    def title_english(self) -> str | None:
        return _first_non_empty(self.payload, "SBJ_ENG_NM")

    @property
    def professor_name(self) -> str | None:
        return _first_non_empty(self.payload, "PROF_KOR_DSC", "EMP_NM")

    @property
    def professor_name_english(self) -> str | None:
        return _first_non_empty(self.payload, "PROF_ENG_DSC")

    @property
    def lecture_time_raw(self) -> str | None:
        return _first_non_empty(self.payload, "TMTBL_KOR_DSC")

    @property
    def lecture_time_english_raw(self) -> str | None:
        return _first_non_empty(self.payload, "TMTBL_ENG_DSC")
