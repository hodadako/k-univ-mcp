from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class GachonDataError(ValueError):
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


@dataclass(slots=True)
class GachonDepartmentRow:
    code: str
    name: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "GachonDepartmentRow":
        code = _first_non_empty(payload, "DPT_CD", "CODE", "value")
        name = _first_non_empty(payload, "LABEL", "DPT_NM", "NAME", "label")
        if not code or not name:
            raise GachonDataError("Gachon department rows must include both code and name.")
        return cls(code=code, name=name, raw=payload)


@dataclass(slots=True)
class GachonCourseRow:
    payload: dict[str, Any]

    @property
    def course_code(self) -> str | None:
        return _first_non_empty(self.payload, "HAKSU_NO")

    @property
    def section(self) -> str | None:
        return _first_non_empty(self.payload, "BUNBAN", "CLASS_DIV", "CLASS_NO")

    @property
    def title(self) -> str | None:
        return _first_non_empty(self.payload, "SUBJECT_NM_KOR")

    @property
    def professor_name(self) -> str | None:
        return _first_non_empty(self.payload, "PROFNM")

    @property
    def lecture_time_raw(self) -> str | None:
        return _first_non_empty(self.payload, "TIME")
