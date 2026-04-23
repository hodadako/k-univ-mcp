from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from k_univ_mcp.models import Course, RawPayloadDump


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


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
