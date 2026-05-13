from dataclasses import dataclass, field
from typing import cast

from k_univ_mcp.providers.hanyang.client import HanyangClient
from k_univ_mcp.providers.hanyang.service import HanyangService


@dataclass
class FakeHanyangClient:
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
        return {
            "DS_PGM": [
                {
                    "list": [
                        {
                            "pgmCd": "HP000011",
                            "pgmNm": "컴퓨터소프트웨어학핵심프로그램",
                            "pgmSosokNm": "서울 공과대학 컴퓨터소프트웨어학부",
                        },
                        {
                            "pgmCd": "HP000012",
                            "pgmNm": "전기공학미래전기에너지특화프로그램",
                            "pgmSosokNm": "서울 공과대학 전기·생체공학부 전기공학전공",
                        },
                        {
                            "pgmCd": "HP000015",
                            "pgmNm": "바이오메디컬공학핵심프로그램",
                            "pgmSosokNm": "서울 공과대학 전기·생체공학부 바이오메디컬공학전공",
                        },
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
                            "jojikGbNm": "서울 대학",
                            "isuTermNm": "1학기",
                            "slgSosokCd": "D001",
                            "slgSosokNm": "컴퓨터소프트웨어학부",
                        },
                        {
                            "suupNo": "22345",
                            "haksuNo": "ELE101",
                            "gwamokNm": "회로이론",
                            "daepyo_gangsa_nm": "이교수",
                            "suupTimes": "화(3)",
                            "suupRoomNms": "공학관 201호",
                            "hakjeom": 3,
                            "isuGbNm": "전공핵심",
                            "banGrade": 2,
                            "campusNm": "서울",
                            "jojikGbNm": "서울 대학",
                            "isuTermNm": "1학기",
                            "slgSosokCd": "D002",
                            "slgSosokNm": "전기공학전공",
                        },
                        {
                            "suupNo": "32345",
                            "haksuNo": "BME101",
                            "gwamokNm": "바이오의공학개론",
                            "daepyo_gangsa_nm": "박교수",
                            "suupTimes": "수(4)",
                            "suupRoomNms": "공학관 301호",
                            "hakjeom": 3,
                            "isuGbNm": "전공핵심",
                            "banGrade": 2,
                            "campusNm": "서울",
                            "jojikGbNm": "서울 대학",
                            "isuTermNm": "1학기",
                            "slgSosokCd": "D003",
                            "slgSosokNm": "바이오메디컬공학전공",
                        },
                    ]
                }
            ]
        }


def test_hanyang_service_reads_static_colleges() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    colleges = service.get_colleges("H0002256", year="2026", semester="1")

    assert [college.code for college in colleges[:4]] == [
        "공과대학",
        "의과대학",
        "간호대학",
        "인문과학대학",
    ]
    assert [college.name for college in colleges[:4]] == [
        "공과대학",
        "의과대학",
        "간호대학",
        "인문과학대학",
    ]


def test_hanyang_service_exposes_default_undergraduate_request_org_codes() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    campuses = service.get_campuses(year="2026", semester="1")

    assert {campus.code: campus.raw["defaultRequestOrgCode"] for campus in campuses} == {
        "seoul": "H0002256",
        "erica": "Y0000316",
    }


def test_hanyang_service_maps_department_name_to_college() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    courses = service.get_courses("2026", "1", "H0002256", "공과대학", "D001")

    assert len(courses) == 1
    assert courses[0].provider == "hanyang"
    assert courses[0].campus_code == "seoul"
    assert courses[0].college_code == "공과대학"
    assert courses[0].college_name == "공과대학"
    assert courses[0].course_code == "CSE101"
    assert client.find_courses_calls == [
        ("2026", "10", "H0002256", "P310278", "M006631", "", 0, 500)
    ]


def test_hanyang_service_splits_electrical_and_biomedical_majors() -> None:
    client = FakeHanyangClient()
    service = HanyangService(client=cast(HanyangClient, cast(object, client)))

    courses = service.get_courses("2026", "1", "H0002256", "공과대학", "seoul")

    by_course_code = {course.course_code: course for course in courses}
    assert by_course_code["ELE101"].college_code == "공과대학"
    assert by_course_code["ELE101"].college_name == "공과대학"
    assert by_course_code["BME101"].college_code == "공과대학"
    assert by_course_code["BME101"].college_name == "공과대학"




def test_hanyang_service_uses_department_priority_and_common_fallbacks() -> None:
    @dataclass
    class CollegeResolutionClient:
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
            return {"DS_PGM": [{"list": []}]}

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
            return {
                "DS_SUUPGS03TTM01": [
                    {
                        "list": [
                            {
                                "suupNo": "1",
                                "haksuNo": "EDU101",
                                "gwamokNm": "교육학개론",
                                "campusNm": "서울",
                                "jojikGbNm": "서울 대학",
                                "isuTermNm": "1학기",
                                "slgSosokCd": "D001",
                                "slgSosokNm": "교육학과",
                                "banSosokNm": "교육학과",
                                "gnjSosokNm": "교육학과",
                            },
                            {
                                "suupNo": "2",
                                "haksuNo": "ATH201",
                                "gwamokNm": "스포츠전공실습",
                                "campusNm": "서울",
                                "jojikGbNm": "서울 대학",
                                "isuTermNm": "1학기",
                                "slgSosokCd": "D002",
                                "slgSosokNm": "서울 대학",
                                "banSosokNm": "서울 대학",
                                "gnjSosokNm": "스포츠사이언스전공",
                            },
                            {
                                "suupNo": "3",
                                "haksuNo": "INV101",
                                "gwamokNm": "사회혁신세미나",
                                "campusNm": "서울",
                                "jojikGbNm": "서울 대학",
                                "isuTermNm": "1학기",
                                "slgSosokCd": "D003",
                                "slgSosokNm": "사회혁신융합전공",
                                "banSosokNm": "사회혁신융합전공",
                                "gnjSosokNm": "사회혁신융합전공",
                            },
                            {
                                "suupNo": "4",
                                "haksuNo": "GEN101",
                                "gwamokNm": "창의융합기초",
                                "campusNm": "서울",
                                "jojikGbNm": "서울 대학",
                                "isuTermNm": "1학기",
                                "slgSosokCd": "D004",
                                "slgSosokNm": "서울 대학",
                                "banSosokNm": "서울 대학",
                                "gnjSosokNm": "창의융합교육팀",
                            },
                            {
                                "suupNo": "5",
                                "haksuNo": "NUR101",
                                "gwamokNm": "간호윤리",
                                "campusNm": "서울",
                                "jojikGbNm": "서울 대학",
                                "isuTermNm": "1학기",
                                "slgSosokCd": "D005",
                                "slgSosokNm": "간호학과(야)",
                                "banSosokNm": "간호학과(야)",
                                "gnjSosokNm": "간호학과(야)",
                            },
                        ]
                    }
                ]
            }

    service = HanyangService(client=cast(HanyangClient, cast(object, CollegeResolutionClient())))

    courses = service.get_courses("2026", "1", "H0002256", "seoul", "seoul")
    by_course_code = {course.course_code: course for course in courses}

    assert by_course_code["EDU101"].college_name == "사범대학"
    assert by_course_code["ATH201"].college_name == "예술·체육대학"
    assert by_course_code["INV101"].college_name == "서울 공통"
    assert by_course_code["GEN101"].college_name == "서울 공통"
    assert by_course_code["NUR101"].college_name == "간호대학"

@dataclass
class PaginatedFakeHanyangClient:
    find_courses_calls: list[tuple[int, int]] = field(default_factory=list)

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
        return {
            "DS_PGM": [
                {
                    "list": [
                        {
                            "pgmCd": "HP000011",
                            "pgmNm": "컴퓨터소프트웨어학핵심프로그램",
                            "pgmSosokNm": "서울 공과대학 컴퓨터소프트웨어학부",
                        }
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
                "jojikGbNm": "서울 대학",
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
    assert courses[0].college_code == "공과대학"
    assert courses[0].college_name == "공과대학"
    assert len(raw_payloads) == 1
    assert len(raw_payloads[0].payload) == 700
    assert client.find_courses_calls == [(0, 500), (500, 500)]
