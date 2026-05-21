from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class MyongjiCourseRow:
    campus: str | None = None
    college: str | None = None
    department: str | None = None
    course_code: str | None = None
    section: str | None = None
    title: str | None = None
    credits: str | None = None
    hours: str | None = None
    recommended_year: str | None = None
    completion_division: str | None = None
    professor: str | None = None
    lecture_time: str | None = None
    classroom: str | None = None
    note: str | None = None
    raw: dict[str, Any] | None = None
