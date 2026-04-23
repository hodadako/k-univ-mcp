from __future__ import annotations

from typing import Protocol

from k_univ_mcp.models import Campus, Course, Faculty, University


class CourseProvider(Protocol):
    def get_campuses(self, *, year: str, semester: str) -> list[Campus]: ...

    def get_universities(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[University]: ...

    def get_faculties(
        self,
        campus_code: str,
        univ_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Faculty]: ...

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[Course]: ...
