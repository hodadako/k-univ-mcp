from dataclasses import dataclass, field
from typing import cast

from k_univ_mcp.providers.hanyang.client import HanyangClient
from k_univ_mcp.providers.hanyang.service import HanyangService


@dataclass
class FakeHanyangClient:
    list_programs_calls: list[tuple[str, str, str, str, str, str]] = field(
        default_factory=list
    )
    find_courses_calls: list[tuple[str, str, str, str, str, str, int, int]] = field(
        default_factory=list
    )

    def list_programs(
        self,
        *,
        year: str,
        semester: str,
        org_code: str,
        pgm_id: str,
        menu_id: str,
        tk: str,
    ) -> dict[str, list[dict[str, list[dict[str, str]]]]]:
        self.list_programs_calls.append((year, semester, org_code, pgm_id, menu_id, tk))
        return {
            "DS_PGM": [
                {
                    "list": [
                        {"pgmCd": "COL01", "pgmNm": "공과대학"},
                        {"pgmCd": "COL02", "pgmNm": "자연과학대학"},
                    ]
                }
            ]
        }

    def find_courses(
        self,
        *,
        year: str,
        semester: str,
        org_code: str,
        pgm_id: str,
        menu_id: str,
        tk: str,
        skip_rows: int = 0,
        max_rows: int = 500,
    ) -> dict[str, list[dict[str, list[dict[str, str | int]]]]]:
        self.find_courses_calls.append(
            (year, semester, org_code, pgm_id, menu_id, tk, skip_rows, max_rows)
        )
        return {
            "DS_SUUPGS03TTM01": [
                {
                    "list": [
                        {
                            "suupNo": "12345",
                            "haksuNo": "CSE101",
                            "gwamokNm": "자료구조",
                            "daepyo_gangsa_nm": "홍길동",
                            "suupTimes": "월(1-2)",
                            "suupRoomNms": "공학관 101호",
                            "hakjeom": 3,
                            "isuGbNm": "전공핵심",
                            "banGrade": 2,
                            "campusNm": "서울",
                            "jojikGbNm": "공과대학",
                            "isuTermNm": "1학기",
                            "slgSosokCd": "D001",
                            "slgSosokNm": "컴퓨터소프트웨어학부",
                        },
                        {
                            "suupNo": "99999",
                            "haksuNo": "BIO101",
                            "gwamokNm": "생물학개론",
                            "daepyo_gangsa_nm": "김교수",
                            "suupTimes": "화(3)",
                            "suupRoomNms": "자연과학관 201호",
                            "hakjeom": 3,
                            "isuGbNm": "전공핵심",
                            "banGrade": 1,
                            "campusNm": "서울",
                            "jojikGbNm": "자연과학대학",
                            "isuTermNm": "1학기",
                            "slgSosokCd": "D999",
                            "slgSosokNm": "생명과학과",
                        },
                    ]
                }
            ]
        }


def test_hanyang_service_reads_colleges_from_program_payload() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    colleges = service.get_colleges("H0002256", year="2026", semester="1")

    assert [college.code for college in colleges] == ["COL01", "COL02"]
    assert [college.name for college in colleges] == ["공과대학", "자연과학대학"]
    assert client.list_programs_calls == [
        ("2026", "10", "H0002256", "P310278", "M006631", "")
    ]


def test_hanyang_service_filters_courses_by_college_and_department() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    courses = service.get_courses("2026", "1", "H0002256", "공과대학", "D001")

    assert len(courses) == 1
    assert courses[0].provider == "hanyang"
    assert courses[0].campus_code == "seoul"
    assert courses[0].course_code == "CSE101"
    assert client.find_courses_calls == [
        ("2026", "10", "H0002256", "P310278", "M006631", "", 0, 500)
    ]


@dataclass
class PaginatedFakeHanyangClient:
    find_courses_calls: list[tuple[int, int]] = field(default_factory=list)

    def find_courses(
        self,
        *,
        year: str,
        semester: str,
        org_code: str,
        pgm_id: str,
        menu_id: str,
        tk: str,
        skip_rows: int = 0,
        max_rows: int = 500,
    ) -> dict[str, list[dict[str, list[dict[str, str | int]]]]]:
        self.find_courses_calls.append((skip_rows, max_rows))

        start = skip_rows
        end = 500 if skip_rows == 0 else 700
        rows = [
            {
                "totalCnt": 700,
                "suupNo": f"{index:05d}",
                "haksuNo": f"CSE{index:04d}",
                "gwamokNm": f"강의 {index}",
                "daepyo_gangsa_nm": "홍길동",
                "suupTimes": "월(1-2)",
                "suupRoomNms": "공학관 101호",
                "hakjeom": 3,
                "isuGbNm": "전공핵심",
                "banGrade": 2,
                "campusNm": "서울",
                "jojikGbNm": "공과대학",
                "isuTermNm": "1학기",
                "slgSosokCd": "D001",
                "slgSosokNm": "컴퓨터소프트웨어학부",
            }
            for index in range(start, end)
        ]
        return {"DS_SUUPGS03TTM01": [{"list": rows}]}


def test_hanyang_service_paginates_course_collection_until_total_count() -> None:
    client = PaginatedFakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    courses, raw_payloads = service.collect_courses(
        year="2026", semester="1", campus_code="seoul"
    )

    assert len(courses) == 700
    assert len(raw_payloads) == 1
    assert len(raw_payloads[0].payload) == 700
    assert client.find_courses_calls == [(0, 500), (500, 500)]
