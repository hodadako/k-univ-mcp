from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class HanyangCourseRow:
    raw: dict[str, Any]

    @property
    def suup_no(self) -> str | None:
        return self.raw.get("suupNo")

    @property
    def haksu_no(self) -> str | None:
        return self.raw.get("haksuNo")

    @property
    def gwamok_nm(self) -> str | None:
        return self.raw.get("gwamokNm")

    @property
    def gwamok_enm(self) -> str | None:
        return self.raw.get("gwamokEnm")

    @property
    def daepyo_gangsa_nm(self) -> str | None:
        return self.raw.get("daepyo_gangsa_nm") or self.raw.get("daepyoGangsaNm")

    @property
    def suup_times(self) -> str | None:
        return self.raw.get("suupTimes")

    @property
    def suup_room_nms(self) -> str | None:
        return self.raw.get("suupRoomNms")

    @property
    def hakjeom(self) -> str | None:
        return str(self.raw.get("hakjeom")) if self.raw.get("hakjeom") is not None else None

    @property
    def isu_gb_nm(self) -> str | None:
        return self.raw.get("isuGbNm")

    @property
    def ban_grade(self) -> str | None:
        return str(self.raw.get("banGrade")) if self.raw.get("banGrade") is not None else None

    @property
    def campus_nm(self) -> str | None:
        return self.raw.get("campusNm")

    @property
    def jojik_gb_nm(self) -> str | None:
        return self.raw.get("jojikGbNm")

    @property
    def isu_term_nm(self) -> str | None:
        return self.raw.get("isuTermNm")

    @property
    def slg_sosok_cd(self) -> str | None:
        return self.raw.get("slgSosokCd")

    @property
    def slg_sosok_nm(self) -> str | None:
        return self.raw.get("slgSosokNm")
