import json

from k_univ_mcp.exporter import export_courses
from k_univ_mcp.models import Course, MeetingSlot, RawPayloadDump


def test_export_courses_writes_all_formats(tmp_path) -> None:
    course = Course(
        provider="yonsei",
        year="2026",
        semester="10",
        term_name="2026-1학기",
        campus_code="s1",
        campus_name="학부(신촌)",
        university_code="s1103",
        university_name="이과대학",
        faculty_code="0301",
        faculty_name="수학전공",
        course_code="MATH1001",
        section="01",
        course_key="MATH1001-01",
        title="미적분학",
        title_english="Calculus",
        professor_name="홍길동",
        professor_name_english="Hong Gil-dong",
        lecture_time_raw="월1,2",
        lecture_time_english_raw=None,
        classroom="과학관",
        classroom_english=None,
        campus_display_name="신촌",
        completion_division_name="전공필수",
        recommended_year="1",
        credits="3",
        recognized_hours=None,
        course_class_name=None,
        evaluation_method_name="상대평가",
        cancelled="N",
        cancelled_label="정상",
        established_department_code="0301",
        established_department_name="수학전공",
        meeting_slots=[MeetingSlot(day_code="MON", day_name="Monday", period=1)],
        parse_warnings=[],
        raw={"subjtnb": "MATH1001"},
    )
    raw_payload = RawPayloadDump(
        provider="yonsei",
        year="2026",
        semester="10",
        campus_code="s1",
        university_code="s1103",
        faculty_code="0301",
        payload=[{"subjtnb": "MATH1001"}],
    )

    artifacts = export_courses([course], tmp_path, "yonsei_2026_10", raw_payloads=[raw_payload])

    assert set(artifacts) == {"csv", "xlsx", "json", "jsonl", "raw_dir"}
    jsonl_text = (tmp_path / "yonsei_2026_10.jsonl").read_text(encoding="utf-8")
    assert "미적분학" in jsonl_text
    raw_files = list((tmp_path / "raw").glob("*.json"))
    assert len(raw_files) == 1
    assert json.loads(raw_files[0].read_text(encoding="utf-8"))[0]["subjtnb"] == "MATH1001"
