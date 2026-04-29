from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from openpyxl import Workbook

from k_univ_mcp.models import Course, MeetingSlot, RawPayloadDump


def _course_from_dict(payload: dict[str, Any]) -> Course:
    meeting_slots = [MeetingSlot(**slot) for slot in payload.get("meeting_slots") or []]
    return Course(
        provider=payload["provider"],
        year=payload["year"],
        semester=payload["semester"],
        term_name=payload.get("term_name"),
        campus_code=payload["campus_code"],
        campus_name=payload.get("campus_name"),
        university_code=payload["university_code"],
        university_name=payload.get("university_name"),
        faculty_code=payload["faculty_code"],
        faculty_name=payload.get("faculty_name"),
        course_code=payload.get("course_code"),
        section=payload.get("section"),
        course_key=payload.get("course_key"),
        title=payload.get("title"),
        title_english=payload.get("title_english"),
        professor_name=payload.get("professor_name"),
        professor_name_english=payload.get("professor_name_english"),
        lecture_time_raw=payload.get("lecture_time_raw"),
        lecture_time_english_raw=payload.get("lecture_time_english_raw"),
        classroom=payload.get("classroom"),
        classroom_english=payload.get("classroom_english"),
        campus_display_name=payload.get("campus_display_name"),
        completion_division_name=payload.get("completion_division_name"),
        recommended_year=payload.get("recommended_year"),
        credits=payload.get("credits"),
        recognized_hours=payload.get("recognized_hours"),
        course_class_name=payload.get("course_class_name"),
        evaluation_method_name=payload.get("evaluation_method_name"),
        cancelled=payload.get("cancelled"),
        cancelled_label=payload.get("cancelled_label"),
        established_department_code=payload.get("established_department_code"),
        established_department_name=payload.get("established_department_name"),
        meeting_slots=meeting_slots,
        parse_warnings=payload.get("parse_warnings") or [],
        raw=payload.get("raw") or {},
    )


def _raw_payload_from_file(raw_path: Path) -> RawPayloadDump:
    provider, year, semester, campus_code, university_code, faculty_code = raw_path.stem.split("_", 5)
    return RawPayloadDump(
        provider=provider,
        year=year,
        semester=semester,
        campus_code=campus_code,
        university_code=university_code,
        faculty_code=faculty_code,
        payload=json.loads(raw_path.read_text(encoding="utf-8")),
    )


def export_courses(
    courses: list[Course],
    outdir: Path,
    stem: str,
    *,
    raw_payloads: list[RawPayloadDump] | None = None,
) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    records = [course.to_export_record() for course in courses]
    dataframe = pd.DataFrame(records)

    csv_path = outdir / f"{stem}.csv"
    xlsx_path = outdir / f"{stem}.xlsx"
    json_path = outdir / f"{stem}.json"
    jsonl_path = outdir / f"{stem}.jsonl"

    dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")
    dataframe.to_excel(xlsx_path, index=False)
    json_path.write_text(
        json.dumps([course.to_dict() for course in courses], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with jsonl_path.open("w", encoding="utf-8") as file_obj:
        for course in courses:
            file_obj.write(json.dumps(course.to_dict(), ensure_ascii=False) + "\n")

    artifacts: dict[str, str] = {
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "json": str(json_path),
        "jsonl": str(jsonl_path),
    }

    if raw_payloads:
        raw_root = outdir / "raw"
        raw_root.mkdir(parents=True, exist_ok=True)
        for raw_payload in raw_payloads:
            raw_path = raw_root / raw_payload.file_name()
            raw_path.write_text(json.dumps(raw_payload.payload, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts["raw_dir"] = str(raw_root)

    return artifacts


def export_course_batches(
    course_batches: Iterable[tuple[list[Course], list[RawPayloadDump]]],
    outdir: Path,
    stem: str,
) -> tuple[dict[str, str], int]:
    outdir.mkdir(parents=True, exist_ok=True)

    csv_path = outdir / f"{stem}.csv"
    xlsx_path = outdir / f"{stem}.xlsx"
    json_path = outdir / f"{stem}.json"
    jsonl_path = outdir / f"{stem}.jsonl"
    raw_root = outdir / "raw"

    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet(title="courses")
    default_sheet = workbook.active
    if default_sheet is not None and default_sheet.title != worksheet.title:
        workbook.remove(default_sheet)

    csv_file = csv_path.open("w", encoding="utf-8-sig", newline="")
    json_file = json_path.open("w", encoding="utf-8")
    jsonl_file = jsonl_path.open("w", encoding="utf-8")

    artifacts: dict[str, str] = {
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
        "json": str(json_path),
        "jsonl": str(jsonl_path),
    }

    fieldnames: list[str] | None = None
    csv_writer: csv.DictWriter[str] | None = None
    row_count = 0
    wrote_json_row = False
    wrote_raw_payload = False

    json_file.write("[")
    try:
        for courses, raw_payloads in course_batches:
            for course in courses:
                export_record = course.to_export_record()
                if fieldnames is None:
                    fieldnames = list(export_record.keys())
                    csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    worksheet.append(fieldnames)

                assert csv_writer is not None
                csv_writer.writerow(export_record)
                worksheet.append([export_record.get(name) for name in fieldnames])

                course_dict = course.to_dict()
                if wrote_json_row:
                    json_file.write(",\n")
                else:
                    json_file.write("\n")
                json_file.write(json.dumps(course_dict, ensure_ascii=False, indent=2))
                jsonl_file.write(json.dumps(course_dict, ensure_ascii=False) + "\n")

                wrote_json_row = True
                row_count += 1

            for raw_payload in raw_payloads:
                if not wrote_raw_payload:
                    raw_root.mkdir(parents=True, exist_ok=True)
                    artifacts["raw_dir"] = str(raw_root)
                    wrote_raw_payload = True
                raw_path = raw_root / raw_payload.file_name()
                raw_path.write_text(json.dumps(raw_payload.payload, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        if wrote_json_row:
            json_file.write("\n]")
        else:
            json_file.write("[]")
        json_file.close()
        jsonl_file.close()
        csv_file.close()
        workbook.save(xlsx_path)

    return artifacts, row_count


def merge_exported_batches(batch_dirs: Iterable[Path], outdir: Path, stem: str) -> tuple[dict[str, str], int]:
    courses: list[Course] = []
    raw_payloads: list[RawPayloadDump] = []
    seen_raw_names: set[str] = set()

    for batch_dir in batch_dirs:
        jsonl_path = batch_dir / f"{stem}.jsonl"
        if jsonl_path.exists():
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                courses.append(_course_from_dict(json.loads(line)))

        raw_root = batch_dir / "raw"
        if raw_root.exists():
            for raw_path in sorted(raw_root.glob("*.json")):
                if raw_path.name in seen_raw_names:
                    continue
                seen_raw_names.add(raw_path.name)
                raw_payloads.append(_raw_payload_from_file(raw_path))

    artifacts = export_courses(courses, outdir, stem, raw_payloads=raw_payloads)
    return artifacts, len(courses)


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
