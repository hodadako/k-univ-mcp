from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from k_univ_mcp.exporter import export_courses, print_json
from k_univ_mcp.providers.dongguk import create_dongguk_service, export_dongguk_courses
from k_univ_mcp.providers.gachon import create_gachon_service
from k_univ_mcp.providers.hanyang import create_hanyang_service
from k_univ_mcp.providers.inha import create_inha_service
from k_univ_mcp.providers.soongsil import create_soongsil_service
from k_univ_mcp.providers.sungshin import create_sungshin_service
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.settings import AppSettings


ProviderFactory = Callable[[AppSettings], Any]


def _add_common_provider_commands(
    provider_parser: argparse.ArgumentParser,
    *,
    provider_label: str,
    include_batch_args: bool = False,
) -> None:
    commands = provider_parser.add_subparsers(dest="command", required=True)

    campuses = commands.add_parser("campuses", help=f"List {provider_label} campuses")
    campuses.add_argument("--year", required=True)
    campuses.add_argument("--semester", required=True)

    colleges = commands.add_parser("colleges", aliases=["universities"], help=f"List {provider_label} colleges for a campus")
    colleges.add_argument("--campus", required=True)
    colleges.add_argument("--year", required=True)
    colleges.add_argument("--semester", required=True)

    departments = commands.add_parser(
        "departments",
        aliases=["faculties"],
        help=f"List {provider_label} departments for a college",
    )
    departments.add_argument("--campus", required=True)
    departments.add_argument("--college", "--univ", dest="college", required=True)
    departments.add_argument("--year", required=True)
    departments.add_argument("--semester", required=True)

    courses = commands.add_parser("courses", help=f"List {provider_label} courses for a department")
    courses.add_argument("--year", required=True)
    courses.add_argument("--semester", required=True)
    courses.add_argument("--campus", required=True)
    courses.add_argument("--college", "--univ", dest="college", required=True)
    courses.add_argument("--department", "--department", dest="department", required=True)

    export = commands.add_parser("export", help=f"Export {provider_label} courses")
    export.add_argument("--year", required=True)
    export.add_argument("--semester", required=True)
    export.add_argument("--campus")
    export.add_argument("--college", "--univ", dest="college")
    export.add_argument("--department", "--department", dest="department")
    export.add_argument("--outdir", default=None)
    if include_batch_args:
        export.add_argument("--batch-index", type=int, default=None)
        export.add_argument("--batch-size", type=int, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="k-univ-mcp CLI")
    provider_parser = parser.add_subparsers(dest="provider", required=True)

    _add_common_provider_commands(provider_parser.add_parser("yonsei", help="Yonsei provider commands"), provider_label="Yonsei")
    _add_common_provider_commands(
        provider_parser.add_parser("dongguk", help="Dongguk provider commands"),
        provider_label="Dongguk",
        include_batch_args=True,
    )
    _add_common_provider_commands(provider_parser.add_parser("gachon", help="Gachon provider commands"), provider_label="Gachon")
    _add_common_provider_commands(provider_parser.add_parser("inha", help="Inha provider commands"), provider_label="Inha")
    _add_common_provider_commands(provider_parser.add_parser("sungshin", help="Sungshin provider commands"), provider_label="Sungshin")
    _add_common_provider_commands(provider_parser.add_parser("soongsil", help="Soongsil provider commands"), provider_label="Soongsil")
    _add_common_provider_commands(provider_parser.add_parser("hanyang", help="Hanyang provider commands"), provider_label="Hanyang")

    return parser


def _print_catalog(service: Any, args: argparse.Namespace) -> int:
    if args.command == "campuses":
        print_json([campus.to_dict() for campus in service.get_campuses(year=args.year, semester=args.semester)])
        return 0
    if args.command == "colleges":
        print_json([college.to_dict() for college in service.get_colleges(args.campus, year=args.year, semester=args.semester)])
        return 0
    if args.command == "departments":
        print_json(
            [
                department.to_dict()
                for department in service.get_departments(
                    args.campus,
                    args.college,
                    year=args.year,
                    semester=args.semester,
                )
            ]
        )
        return 0
    if args.command == "courses":
        print_json(
            [
                course.to_dict()
                for course in service.get_courses(
                    args.year,
                    args.semester,
                    args.campus,
                    args.college,
                    args.department,
                )
            ]
        )
        return 0
    return -1


def _export_with_default_stem(
    service: Any,
    settings: AppSettings,
    args: argparse.Namespace,
) -> int:
    courses, raw_payloads = service.collect_courses(
        year=args.year,
        semester=args.semester,
        campus_code=args.campus,
        college_code=args.college,
        department_code=args.department,
    )
    outdir = Path(args.outdir) if args.outdir else settings.output_dir
    stem = f"{args.provider}_{args.year}_{args.semester}"
    artifacts = export_courses(courses, outdir, stem, raw_payloads=raw_payloads)
    print_json({"artifacts": artifacts, "row_count": len(courses)})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    factories: dict[str, ProviderFactory] = {
        "yonsei": create_yonsei_service,
        "dongguk": create_dongguk_service,
        "gachon": create_gachon_service,
        "inha": lambda _settings: create_inha_service(),
        "sungshin": create_sungshin_service,
        "soongsil": create_soongsil_service,
        "hanyang": create_hanyang_service,
    }

    service = factories[args.provider](settings)
    printed = _print_catalog(service, args)
    if printed == 0:
        return 0

    if args.command != "export":
        parser.error(f"Unsupported command: {args.command}")

    if args.provider == "dongguk":
        outdir = Path(args.outdir) if args.outdir else settings.output_dir
        result = export_dongguk_courses(
            service,
            year=args.year,
            semester=args.semester,
            outdir=outdir,
            campus_code=args.campus,
            college_code=args.college,
            department_code=args.department,
            batch_index=args.batch_index,
            batch_size=args.batch_size,
        )
        print_json(result)
        return 0

    return _export_with_default_stem(service, settings, args)


if __name__ == "__main__":
    raise SystemExit(main())
