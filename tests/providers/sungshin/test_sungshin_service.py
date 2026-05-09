from dataclasses import dataclass, field

from k_univ_mcp.providers.sungshin.service import SungshinService


@dataclass
class FakeSungshinClient:
    fetch_courses_calls: list[tuple[str, str, str, str, str]] = field(
        default_factory=list
    )

    def onload(self) -> dict[str, list[dict[str, str]]]:
        return {
            "deptList": [
                {
                    "orgClsfCd": "COMM075.101",
                    "cmnCd": "D001",
                    "cmnCdNm": "[대학]컴퓨터공학과",
                },
                {
                    "orgClsfCd": "OTHER",
                    "cmnCd": "D999",
                    "cmnCdNm": "[대학]무시대상",
                },
            ]
        }

    def fetch_courses(
        self,
        *,
        year: str,
        semester: str,
        cmp_code: str,
        org_clsf_code: str,
        dpt_mjr_code: str,
    ) -> list[dict[str, str]]:
        self.fetch_courses_calls.append(
            (year, semester, cmp_code, org_clsf_code, dpt_mjr_code)
        )
        return [
            {
                "sbjNm": "자료구조",
                "sbjEnm": "Data Structures",
                "sbjNo": "CSE101",
                "dvcls": "001",
                "profDsc": "홍길동",
                "tmtblKorDsc": "월/1-3",
                "roomKorDsc": "수정관 101",
                "cmpCdNm": "수정",
                "cpdivNm": "전공",
                "cdtHcnt": "3.0/3.0/0.0",
                "semCd": semester,
                "orgClsfCd": org_clsf_code,
                "crsNm": "학사과정",
                "dptMjrCd": dpt_mjr_code,
                "opDptmjrNm": "컴퓨터공학과",
            }
        ]


def test_sungshin_service_filters_departments_from_onload() -> None:
    service = SungshinService(client=FakeSungshinClient())

    departments = service.get_departments(
        "COMM060.1", "COMM075.101", year="2026", semester="1"
    )

    assert len(departments) == 1
    assert departments[0].campus_code == "sujeong"
    assert departments[0].code == "D001"
    assert departments[0].name == "컴퓨터공학과"


def test_sungshin_service_normalizes_codes_for_course_queries() -> None:
    client = FakeSungshinClient()
    service = SungshinService(client=client)

    courses = service.get_courses("2026", "1", "COMM060.1", "COMM075.101", "D001")

    assert client.fetch_courses_calls == [
        ("2026", "COMM063.10", "COMM060.1", "COMM075.101", "D001")
    ]
    assert len(courses) == 1
    assert courses[0].provider == "sungshin"
    assert courses[0].campus_code == "sujeong"
    assert courses[0].course_key == "CSE101-001"
