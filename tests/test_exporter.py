import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import k_univ_mcp.exporter as exporter_module
from k_univ_mcp.exporter import export_course_batches, export_courses, merge_exported_batches, resolve_provider_outdir
from k_univ_mcp.models import Course, MeetingSlot, RawPayloadDump


@dataclass
class MemoryPath:
    parts: tuple[str, ...]
    files: dict[str, str] = field(default_factory=dict)
    directories: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.directories.add(self._key())

    def __truediv__(self, child: str) -> "MemoryPath":
        return MemoryPath(self.parts + (child,), self.files, self.directories)

    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        _ = parents, exist_ok
        self.directories.add(self._key())

    def write_text(self, value: str, encoding: str = "utf-8") -> None:
        _ = encoding
        self.files[self._key()] = value

    def read_text(self, encoding: str = "utf-8") -> str:
        _ = encoding
        return self.files[self._key()]

    def exists(self) -> bool:
        return self._key() in self.files or self._key() in self.directories

    def open(self, mode: str, encoding: str = "utf-8", newline: str | None = None):
        _ = encoding, newline
        if mode != "w":
            raise AssertionError(f"Unsupported mode in test fake path: {mode}")
        return MemoryFile(self.files, self._key())

    def glob(self, pattern: str) -> list["MemoryPath"]:
        if pattern != "*.json":
            raise AssertionError(f"Unsupported glob pattern in test fake path: {pattern}")
        prefix = f"{self._key()}/"
        matches = [path for path in self.files if path.startswith(prefix) and path.endswith(".json")]
        return [MemoryPath(tuple(path.split("/")), self.files, self.directories) for path in sorted(matches)]

    def _key(self) -> str:
        return "/".join(self.parts)

    @property
    def name(self) -> str:
        return self.parts[-1]

    @property
    def stem(self) -> str:
        return self.name.rsplit(".", 1)[0]

    def __str__(self) -> str:
        return self._key()


class MemoryFile(io.StringIO):
    def __init__(self, files: dict[str, str], key: str) -> None:
        super().__init__()
        self._files = files
        self._key = key

    def close(self) -> None:
        self._files[self._key] = self.getvalue()
        super().close()


class FakeDataFrame:
    last_records: list[dict[str, object]] | None = None
    csv_calls: list[tuple[str, bool, str]] = []
    excel_calls: list[tuple[str, bool]] = []

    def __init__(self, records: list[dict[str, object]]) -> None:
        type(self).last_records = records

    def to_csv(self, path: MemoryPath, index: bool = False, encoding: str = "utf-8") -> None:
        type(self).csv_calls.append((str(path), index, encoding))

    def to_excel(self, path: MemoryPath, index: bool = False) -> None:
        type(self).excel_calls.append((str(path), index))


class FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title
        self.rows: list[list[object]] = []

    def append(self, row: list[object]) -> None:
        self.rows.append(row)


class FakeWorkbook:
    saved_paths: list[str] = []
    last_sheet: FakeWorksheet | None = None

    def __init__(self, write_only: bool = False) -> None:
        self.write_only = write_only
        self.active = FakeWorksheet("Sheet")

    def create_sheet(self, title: str) -> FakeWorksheet:
        sheet = FakeWorksheet(title)
        type(self).last_sheet = sheet
        return sheet

    def remove(self, sheet: FakeWorksheet) -> None:
        _ = sheet

    def save(self, path: MemoryPath) -> None:
        type(self).saved_paths.append(str(path))


def make_root() -> MemoryPath:
    return MemoryPath(("test_out",))


def make_course(*, provider: str, semester: str, course_code: str, title: str, campus_code: str, campus_name: str, college_code: str, college_name: str, department_code: str, department_name: str, raw: dict[str, object]) -> Course:
    return Course(
        provider=provider,
        year="2026",
        semester=semester,
        semester_name="2026-1학기" if provider == "yonsei" else "1학기",
        campus_code=campus_code,
        campus_name=campus_name,
        college_code=college_code,
        college_name=college_name,
        department_code=department_code,
        department_name=department_name,
        course_code=course_code,
        section="01",
        course_key=f"{course_code}-01",
        title=title,
        title_english=None,
        professor_name="홍길동",
        professor_name_english=None,
        lecture_time_raw="월 1교시",
        lecture_time_english_raw=None,
        classroom="A101",
        classroom_english=None,
        campus_display_name=campus_name,
        completion_division_name="학사과정",
        recommended_year="1학년",
        credits="3.0",
        recognized_hours="3.0",
        course_class_name="일반강의",
        evaluation_method_name="상대평가",
        cancelled=None,
        cancelled_label=None,
        established_department_code=department_code,
        established_department_name=department_name,
        meeting_slots=[MeetingSlot(day_code="MON", day_name="Monday", period=1)],
        parse_warnings=[],
        raw=raw,
    )


def test_export_courses_writes_all_formats_without_filesystem(monkeypatch) -> None:
    root = make_root()
    course = make_course(
        provider="yonsei",
        semester="10",
        course_code="MATH1001",
        title="미적분학",
        campus_code="sinchon-undergraduate",
        campus_name="연세대학교 신촌캠퍼스 학부",
        college_code="s1103",
        college_name="이과대학",
        department_code="0301",
        department_name="수학전공",
        raw={"subjtnb": "MATH1001"},
    )
    raw_payload = RawPayloadDump(
        provider="yonsei",
        year="2026",
        semester="10",
        campus_code="sinchon-undergraduate",
        college_code="s1103",
        department_code="0301",
        payload=[{"subjtnb": "MATH1001"}],
    )

    FakeDataFrame.csv_calls = []
    FakeDataFrame.excel_calls = []
    FakeDataFrame.last_records = None
    monkeypatch.setattr(exporter_module.pd, "DataFrame", FakeDataFrame)

    artifacts = export_courses([course], cast(Path, cast(object, root)), "yonsei_2026_10", raw_payloads=[raw_payload])

    assert set(artifacts) == {"csv", "xlsx", "json", "jsonl", "raw_dir"}
    assert FakeDataFrame.csv_calls == [("test_out/yonsei_2026_10.csv", False, "utf-8-sig")]
    assert FakeDataFrame.excel_calls == [("test_out/yonsei_2026_10.xlsx", False)]
    assert FakeDataFrame.last_records is not None
    assert FakeDataFrame.last_records[0]["title"] == "미적분학"
    assert "미적분학" in root.files["test_out/yonsei_2026_10.jsonl"]
    assert json.loads(root.files["test_out/raw/yonsei_2026_10_sinchon-undergraduate_s1103_0301.json"])[0]["subjtnb"] == "MATH1001"


def test_resolve_provider_outdir_uses_school_name_directory() -> None:
    outdir = resolve_provider_outdir(Path("out"), "yonsei")

    assert outdir == Path("out") / "yonsei"


def test_export_course_batches_streams_multiple_batches_without_filesystem(monkeypatch) -> None:
    root = make_root()
    course1 = make_course(
        provider="dongguk",
        semester="CM160.10",
        course_code="BUD10126",
        title="불교학맵핑",
        campus_code="wise",
        campus_name="동국대학교 WISE캠퍼스",
        college_code="DK0201",
        college_name="불교문화대학",
        department_code="DK02010101",
        department_name="불교학부",
        raw={"SBJ_NO": "BUD10126"},
    )
    course2 = make_course(
        provider="dongguk",
        semester="CM160.10",
        course_code="KOR1001",
        title="국어학개론",
        campus_code="wise",
        campus_name="동국대학교 WISE캠퍼스",
        college_code="DK0202",
        college_name="인문과학대학",
        department_code="DK02020101",
        department_name="국어국문학과",
        raw={"SBJ_NO": "KOR1001"},
    )
    raw_payload1 = RawPayloadDump(
        provider="dongguk",
        year="2026",
        semester="CM160.10",
        campus_code="wise",
        college_code="DK0201",
        department_code="DK02010101",
        payload=[{"SBJ_NO": "BUD10126"}],
    )
    raw_payload2 = RawPayloadDump(
        provider="dongguk",
        year="2026",
        semester="CM160.10",
        campus_code="wise",
        college_code="DK0202",
        department_code="DK02020101",
        payload=[{"SBJ_NO": "KOR1001"}],
    )

    FakeWorkbook.saved_paths = []
    FakeWorkbook.last_sheet = None
    monkeypatch.setattr(exporter_module, "Workbook", FakeWorkbook)

    artifacts, row_count = export_course_batches(
        [([course1], [raw_payload1]), ([course2], [raw_payload2])],
        cast(Path, cast(object, root)),
        "dongguk_2026_CM160.10",
    )

    assert row_count == 2
    assert set(artifacts) == {"csv", "xlsx", "json", "jsonl", "raw_dir"}
    assert "불교학맵핑" in root.files["test_out/dongguk_2026_CM160.10.json"]
    assert "국어학개론" in root.files["test_out/dongguk_2026_CM160.10.json"]
    assert json.loads(root.files["test_out/raw/dongguk_2026_CM160.10_wise_DK0201_DK02010101.json"])[0]["SBJ_NO"] == "BUD10126"
    assert json.loads(root.files["test_out/raw/dongguk_2026_CM160.10_wise_DK0202_DK02020101.json"])[0]["SBJ_NO"] == "KOR1001"
    assert FakeWorkbook.saved_paths == ["test_out/dongguk_2026_CM160.10.xlsx"]
    assert FakeWorkbook.last_sheet is not None
    assert FakeWorkbook.last_sheet.rows[0][0] == "provider"
    assert FakeWorkbook.last_sheet.rows[1][0] == "dongguk"
    assert FakeWorkbook.last_sheet.rows[2][0] == "dongguk"


def test_merge_exported_batches_merges_batch_artifacts_without_filesystem(monkeypatch) -> None:
    root = make_root()
    batch0 = root / "batch-0"
    batch1 = root / "batch-1"
    batch0.mkdir(parents=True, exist_ok=True)
    batch1.mkdir(parents=True, exist_ok=True)

    course1 = make_course(
        provider="dongguk",
        semester="CM160.10",
        course_code="BUD10126",
        title="불교학맵핑",
        campus_code="wise",
        campus_name="동국대학교 WISE캠퍼스",
        college_code="DK0201",
        college_name="불교문화대학",
        department_code="DK02010101",
        department_name="불교학부",
        raw={"SBJ_NO": "BUD10126"},
    )
    course2 = make_course(
        provider="dongguk",
        semester="CM160.10",
        course_code="KOR1001",
        title="국어학개론",
        campus_code="wise",
        campus_name="동국대학교 WISE캠퍼스",
        college_code="DK0202",
        college_name="인문과학대학",
        department_code="DK02020101",
        department_name="국어국문학과",
        raw={"SBJ_NO": "KOR1001"},
    )
    (batch0 / "dongguk_2026_CM160.10.jsonl").write_text(json.dumps(course1.to_dict(), ensure_ascii=False) + "\n")
    (batch1 / "dongguk_2026_CM160.10.jsonl").write_text(json.dumps(course2.to_dict(), ensure_ascii=False) + "\n")

    raw0 = batch0 / "raw"
    raw1 = batch1 / "raw"
    raw0.mkdir(parents=True, exist_ok=True)
    raw1.mkdir(parents=True, exist_ok=True)
    (raw0 / "dongguk_2026_CM160.10_wise_DK0201_DK02010101.json").write_text(
        json.dumps([{"SBJ_NO": "BUD10126"}], ensure_ascii=False)
    )
    (raw1 / "dongguk_2026_CM160.10_wise_DK0202_DK02020101.json").write_text(
        json.dumps([{"SBJ_NO": "KOR1001"}], ensure_ascii=False)
    )

    FakeDataFrame.csv_calls = []
    FakeDataFrame.excel_calls = []
    FakeDataFrame.last_records = None
    monkeypatch.setattr(exporter_module.pd, "DataFrame", FakeDataFrame)

    artifacts, row_count = merge_exported_batches(
        [cast(Path, cast(object, batch0)), cast(Path, cast(object, batch1))],
        cast(Path, cast(object, root)),
        "dongguk_2026_CM160.10",
    )

    assert row_count == 2
    assert set(artifacts) == {"csv", "xlsx", "json", "jsonl", "raw_dir"}
    assert FakeDataFrame.last_records is not None
    records = cast(list[dict[str, object]], FakeDataFrame.last_records)
    assert [record["title"] for record in records] == ["불교학맵핑", "국어학개론"]
    assert "불교학맵핑" in root.files["test_out/dongguk_2026_CM160.10.jsonl"]
    assert "국어학개론" in root.files["test_out/dongguk_2026_CM160.10.jsonl"]
    assert json.loads(root.files["test_out/raw/dongguk_2026_CM160.10_wise_DK0201_DK02010101.json"])[0]["SBJ_NO"] == "BUD10126"
