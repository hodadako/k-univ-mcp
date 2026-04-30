from dataclasses import dataclass, field
from typing import Any

from k_univ_mcp.providers.inha.service import InhaService


@dataclass
class FakeInhaClient:
    def fetch_departments_from_curriculum(self, year: str | None = None) -> list[dict[str, str]]:
        return [
            {"code": "0194002", "name": "기계공학과 / 기계공학", "university": "공과대학"},
            {"code": "1063157", "name": "수학과 / 수학", "university": "자연과학대학"},
        ]

    def fetch_departments(self) -> list[dict[str, str]]:
        return [
            {"code": "0194002", "name": "기계공학과 / 기계공학"},
            {"code": "1063157", "name": "수학과 / 수학"},
        ]

    def fetch_courses(self, faculty_code: str, year: str | None = None, semester: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "haksu_section": "ME101-001",
                "title": "기계공학개론",
                "grade": "1",
                "credits": "3.0",
                "category": "전필",
                "time_location": "월1,2,3(5-101)",
                "professor": "홍길동",
                "evaluation": "상대평가",
                "note": "",
                "raw_tds": []
            }
        ]


def test_inha_service_returns_campuses() -> None:
    service = InhaService(client=FakeInhaClient())
    campuses = service.get_campuses(year="2026", semester="1")
    assert len(campuses) == 1
    assert campuses[0].code == "yonghyeon"


def test_inha_service_returns_universities() -> None:
    service = InhaService(client=FakeInhaClient())
    universities = service.get_universities("yonghyeon", year="2026", semester="1")
    assert len(universities) == 2
    assert {u.name for u in universities} == {"공과대학", "자연과학대학"}


def test_inha_service_returns_faculties() -> None:
    service = InhaService(client=FakeInhaClient())
    faculties = service.get_faculties("yonghyeon", "공과대학", year="2026", semester="1")
    assert len(faculties) == 1
    assert faculties[0].name == "기계공학과 / 기계공학"


def test_inha_service_returns_courses() -> None:
    service = InhaService(client=FakeInhaClient())
    courses = service.get_courses("2026", "1", "yonghyeon", "공과대학", "0194002")
    assert len(courses) == 1
    assert courses[0].title == "기계공학개론"
    assert courses[0].course_code == "ME101"
    assert len(courses[0].meeting_slots) == 3
