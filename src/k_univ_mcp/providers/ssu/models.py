from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SsuCourseRow:
    plan: str
    completion_division_major: str
    completion_division_multimajor: str
    engineering_certification: str
    course_number: str
    course_name: str
    syllabus_info: str
    section: str
    professor: str
    department: str
    time_credits: str
    capacity: str
    vacancy: str
    time_location: str
    target_audience: str
    raw: dict[str, Any]
