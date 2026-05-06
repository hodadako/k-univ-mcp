from __future__ import annotations

from typing import Protocol

from k_univ_mcp.models import Campus, Course, Department, College


class CourseProvider(Protocol):
    def get_campuses(self, *, year: str, semester: str) -> list[Campus]: ...

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]: ...

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]: ...

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[Course]: ...
