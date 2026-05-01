from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InhaCourseRow:
    haksu_section: str  # 학수번호-분반
    title: str          # 과목명
    grade: str          # 학년
    credits: str        # 학점
    category: str       # 과목구분
    time_location: str  # 시간 및 강의실
    professor: str      # 담당교수
    evaluation: str     # 평가방식
    note: str           # 비고
    raw: dict[str, Any]

    @property
    def course_code(self) -> str:
        if "-" in self.haksu_section:
            return self.haksu_section.split("-")[0]
        return self.haksu_section

    @property
    def section(self) -> str:
        if "-" in self.haksu_section:
            return self.haksu_section.split("-")[1]
        return ""
