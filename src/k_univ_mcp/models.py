from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Campus:
    code: str
    name: str
    english_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class University:
    campus_code: str
    code: str
    name: str
    english_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Faculty:
    campus_code: str
    university_code: str
    code: str
    name: str
    english_name: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MeetingSlot:
    day_code: str
    day_name: str
    period: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Course:
    provider: str
    year: str
    semester: str
    term_name: str | None
    campus_code: str
    campus_name: str | None
    university_code: str
    university_name: str | None
    faculty_code: str
    faculty_name: str | None
    course_code: str | None
    section: str | None
    course_key: str | None
    title: str | None
    title_english: str | None
    professor_name: str | None
    professor_name_english: str | None
    lecture_time_raw: str | None
    lecture_time_english_raw: str | None
    classroom: str | None
    classroom_english: str | None
    campus_display_name: str | None
    completion_division_name: str | None
    recommended_year: str | None
    credits: str | None
    recognized_hours: str | None
    course_class_name: str | None
    evaluation_method_name: str | None
    cancelled: str | None
    cancelled_label: str | None
    established_department_code: str | None
    established_department_name: str | None
    meeting_slots: list[MeetingSlot] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    def to_export_record(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "year": self.year,
            "semester": self.semester,
            "term_name": self.term_name,
            "campus_code": self.campus_code,
            "campus_name": self.campus_name,
            "university_code": self.university_code,
            "university_name": self.university_name,
            "faculty_code": self.faculty_code,
            "faculty_name": self.faculty_name,
            "course_code": self.course_code,
            "section": self.section,
            "course_key": self.course_key,
            "title": self.title,
            "title_english": self.title_english,
            "professor_name": self.professor_name,
            "professor_name_english": self.professor_name_english,
            "lecture_time_raw": self.lecture_time_raw,
            "lecture_time_english_raw": self.lecture_time_english_raw,
            "classroom": self.classroom,
            "classroom_english": self.classroom_english,
            "campus_display_name": self.campus_display_name,
            "completion_division_name": self.completion_division_name,
            "recommended_year": self.recommended_year,
            "credits": self.credits,
            "recognized_hours": self.recognized_hours,
            "course_class_name": self.course_class_name,
            "evaluation_method_name": self.evaluation_method_name,
            "cancelled": self.cancelled,
            "cancelled_label": self.cancelled_label,
            "established_department_code": self.established_department_code,
            "established_department_name": self.established_department_name,
            "meeting_slots_json": json.dumps([slot.to_dict() for slot in self.meeting_slots], ensure_ascii=False),
            "parse_warnings_json": json.dumps(self.parse_warnings, ensure_ascii=False),
            "raw_json": json.dumps(self.raw, ensure_ascii=False),
        }


@dataclass(slots=True)
class RawPayloadDump:
    provider: str
    year: str
    semester: str
    campus_code: str
    university_code: str
    faculty_code: str
    payload: list[dict[str, Any]]

    def file_name(self) -> str:
        return f"{self.provider}_{self.year}_{self.semester}_{self.campus_code}_{self.university_code}_{self.faculty_code}.json"


@dataclass(slots=True)
class SearchParams:
    query: str
    year: str | None = None
    semester: str | None = None
