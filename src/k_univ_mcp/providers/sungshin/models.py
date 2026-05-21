from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SungshinCourseRow:
    payload: dict[str, Any]

    @property
    def course_code(self) -> str | None:
        return self.payload.get("sbjNo")

    @property
    def section(self) -> str | None:
        return self.payload.get("dvcls")

    @property
    def title(self) -> str | None:
        return self.payload.get("sbjNm")

    @property
    def title_english(self) -> str | None:
        return self.payload.get("sbjEnm")

    @property
    def professor_name(self) -> str | None:
        return self.payload.get("profDsc")

    @property
    def lecture_time_raw(self) -> str | None:
        return self.payload.get("tmtblKorDsc")
