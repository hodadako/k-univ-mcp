from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class YonseiSeedDataError(ValueError):
    pass


@dataclass(slots=True)
class YonseiDepartmentRow:
    code: str
    name: str
    english_name: str | None
    system_division_code: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "YonseiDepartmentRow":
        department_code = payload.get("deptCd")
        department_name = payload.get("deptNm")
        if not department_code or not department_name:
            raise YonseiSeedDataError("Yonsei department seed rows must include both deptCd and deptNm.")
        return cls(
            code=str(department_code),
            name=str(department_name),
            english_name=payload.get("engDeptNm"),
            system_division_code=payload.get("sysinstDivCd"),
            raw=payload,
        )


@dataclass(slots=True)
class YonseiCourseRow:
    payload: dict[str, Any]

    @property
    def course_code(self) -> str | None:
        return self.payload.get("subjtnb")

    @property
    def section(self) -> str | None:
        return self.payload.get("corseDvclsNo")

    @property
    def title(self) -> str | None:
        return self.payload.get("subjtNm")

    @property
    def title_english(self) -> str | None:
        return self.payload.get("subjtEngNm")

    @property
    def professor_name(self) -> str | None:
        return self.payload.get("cgprfNm")

    @property
    def lecture_time_raw(self) -> str | None:
        return self.payload.get("lctreTimeNm")
