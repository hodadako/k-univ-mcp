from dataclasses import dataclass, field

from k_univ_mcp.providers.gachon.service import GACHON_GLOBAL_CAMPUS_CODE, GACHON_MEDICAL_CAMPUS_CODE, GachonService


@dataclass
class FakeClient:
    university_calls: list[str] = field(default_factory=list)
    faculty_calls: list[tuple[str, str, str, str]] = field(default_factory=list)
    course_calls: list[tuple[str, str, str, str, str]] = field(default_factory=list)

    def list_universities(self, group_type: str):
        self.university_calls.append(group_type)
        if group_type == "20":
            return ([{"YEAR": "2026", "TERM_CD": "10"}], [{"DPT_CD": "COL01", "LABEL": "AI대학"}])
        return ([{"YEAR": "2026", "TERM_CD": "10"}], [{"DPT_CD": "MED01", "LABEL": "의과대학"}])

    def list_faculties(self, year: str, semester: str, group_type: str, univ_code: str):
        self.faculty_calls.append((year, semester, group_type, univ_code))
        if group_type == "20":
            return [{"DPT_CD": "D001", "LABEL": "컴퓨터공학과"}]
        return [{"DPT_CD": "M001", "LABEL": "의예과"}]

    def list_courses(self, year: str, semester: str, group_type: str, univ_code: str, faculty_code: str):
        self.course_calls.append((year, semester, group_type, univ_code, faculty_code))
        return [
            {
                "HAKSU_NO": "CSE101" if group_type == "20" else "MED101",
                "SUBJECT_NM_KOR": "자료구조 " if group_type == "20" else "해부학 ",
                "PROFNM": "홍길동",
                "TIME": "수4 ,수5 ,수6",
                "LOC_NM": "A101",
                "ISU_NM": "전필",
                "PRINT_DPT": "컴퓨터공학과" if group_type == "20" else "의예과",
                "SISU": "3",
            }
        ]


def test_service_returns_single_synthetic_campus() -> None:
    service = GachonService(client=FakeClient())

    campuses = service.get_campuses(year="2026", semester="10")

    assert [campus.code for campus in campuses] == [GACHON_GLOBAL_CAMPUS_CODE, GACHON_MEDICAL_CAMPUS_CODE]


def test_service_collects_courses_and_raw_payloads() -> None:
    client = FakeClient()
    service = GachonService(client=client)

    courses, raw_payloads = service.collect_courses(year="2026", semester="10")

    assert len(courses) == 2
    assert len(raw_payloads) == 2
    assert [course.provider for course in courses] == ["gachon", "gachon"]
    assert [course.campus_code for course in courses] == [GACHON_GLOBAL_CAMPUS_CODE, GACHON_MEDICAL_CAMPUS_CODE]
    assert [course.title for course in courses] == ["자료구조", "해부학"]
    assert client.university_calls == ["20", "21"]
    assert client.faculty_calls == [("2026", "10", "20", "COL01"), ("2026", "10", "21", "MED01")]
    assert client.course_calls == [("2026", "10", "20", "COL01", "D001"), ("2026", "10", "21", "MED01", "M001")]


def test_service_rejects_unknown_campus_code() -> None:
    service = GachonService(client=FakeClient())

    try:
        service.get_universities("other", year="2026", semester="10")
    except ValueError as exc:
        assert "Unsupported Gachon campus code" in str(exc)
    else:
        raise AssertionError("Expected GachonService to reject unsupported campus code.")
