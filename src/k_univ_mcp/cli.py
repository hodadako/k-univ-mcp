from __future__ import annotations

import argparse
from pathlib import Path

from k_univ_mcp.exporter import export_courses, print_json
from k_univ_mcp.providers.dongguk import create_dongguk_service, export_dongguk_courses
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.settings import AppSettings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="k-univ-mcp CLI")
    provider_parser = parser.add_subparsers(dest="provider", required=True)

    yonsei_parser = provider_parser.add_parser("yonsei", help="Yonsei provider commands")
    yonsei_commands = yonsei_parser.add_subparsers(dest="command", required=True)

    campuses = yonsei_commands.add_parser("campuses", help="List Yonsei campuses")
    campuses.add_argument("--year", required=True)
    campuses.add_argument("--semester", required=True)

    universities = yonsei_commands.add_parser("universities", help="List Yonsei universities for a campus")
    universities.add_argument("--campus", required=True)
    universities.add_argument("--year", required=True)
    universities.add_argument("--semester", required=True)

    faculties = yonsei_commands.add_parser("faculties", help="List Yonsei faculties for a university")
    faculties.add_argument("--campus", required=True)
    faculties.add_argument("--univ", required=True)
    faculties.add_argument("--year", required=True)
    faculties.add_argument("--semester", required=True)

    courses = yonsei_commands.add_parser("courses", help="List Yonsei courses for a faculty")
    courses.add_argument("--year", required=True)
    courses.add_argument("--semester", required=True)
    courses.add_argument("--campus", required=True)
    courses.add_argument("--univ", required=True)
    courses.add_argument("--faculty", required=True)

    export = yonsei_commands.add_parser("export", help="Export Yonsei courses")
    export.add_argument("--year", required=True)
    export.add_argument("--semester", required=True)
    export.add_argument("--campus")
    export.add_argument("--univ")
    export.add_argument("--faculty")
    export.add_argument("--outdir", default=None)

    dongguk_parser = provider_parser.add_parser("dongguk", help="Dongguk provider commands")
    dongguk_commands = dongguk_parser.add_subparsers(dest="command", required=True)

    dongguk_campuses = dongguk_commands.add_parser("campuses", help="List Dongguk campuses")
    dongguk_campuses.add_argument("--year", required=True)
    dongguk_campuses.add_argument("--semester", required=True)

    dongguk_universities = dongguk_commands.add_parser("universities", help="List Dongguk universities for a campus")
    dongguk_universities.add_argument("--campus", required=True)
    dongguk_universities.add_argument("--year", required=True)
    dongguk_universities.add_argument("--semester", required=True)

    dongguk_faculties = dongguk_commands.add_parser("faculties", help="List Dongguk faculties for a university")
    dongguk_faculties.add_argument("--campus", required=True)
    dongguk_faculties.add_argument("--univ", required=True)
    dongguk_faculties.add_argument("--year", required=True)
    dongguk_faculties.add_argument("--semester", required=True)

    dongguk_courses = dongguk_commands.add_parser("courses", help="List Dongguk courses for a faculty")
    dongguk_courses.add_argument("--year", required=True)
    dongguk_courses.add_argument("--semester", required=True)
    dongguk_courses.add_argument("--campus", required=True)
    dongguk_courses.add_argument("--univ", required=True)
    dongguk_courses.add_argument("--faculty", required=True)

    dongguk_export = dongguk_commands.add_parser("export", help="Export Dongguk courses")
    dongguk_export.add_argument("--year", required=True)
    dongguk_export.add_argument("--semester", required=True)
    dongguk_export.add_argument("--campus")
    dongguk_export.add_argument("--univ")
    dongguk_export.add_argument("--faculty")
    dongguk_export.add_argument("--batch-index", type=int, default=None)
    dongguk_export.add_argument("--batch-size", type=int, default=None)
    dongguk_export.add_argument("--outdir", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    if args.provider == "yonsei":
        service = create_yonsei_service(settings)
        if args.command == "campuses":
            campuses = service.get_campuses(year=args.year, semester=args.semester)
            print_json([campus.to_dict() for campus in campuses])
            return 0
        if args.command == "universities":
            universities = service.get_universities(args.campus, year=args.year, semester=args.semester)
            print_json([university.to_dict() for university in universities])
            return 0
        if args.command == "faculties":
            faculties = service.get_faculties(args.campus, args.univ, year=args.year, semester=args.semester)
            print_json([faculty.to_dict() for faculty in faculties])
            return 0
        if args.command == "courses":
            courses = service.get_courses(args.year, args.semester, args.campus, args.univ, args.faculty)
            print_json([course.to_dict() for course in courses])
            return 0
        if args.command == "export":
            courses, raw_payloads = service.collect_courses(
                year=args.year,
                semester=args.semester,
                campus_code=args.campus,
                univ_code=args.univ,
                faculty_code=args.faculty,
            )
            outdir = Path(args.outdir) if args.outdir else settings.output_dir
            stem = f"yonsei_{args.year}_{args.semester}"
            artifacts = export_courses(courses, outdir, stem, raw_payloads=raw_payloads)
            print_json({"artifacts": artifacts, "row_count": len(courses)})
            return 0

    if args.provider == "dongguk":
        service = create_dongguk_service(settings)
        if args.command == "campuses":
            campuses = service.get_campuses(year=args.year, semester=args.semester)
            print_json([campus.to_dict() for campus in campuses])
            return 0
        if args.command == "universities":
            universities = service.get_universities(args.campus, year=args.year, semester=args.semester)
            print_json([university.to_dict() for university in universities])
            return 0
        if args.command == "faculties":
            faculties = service.get_faculties(args.campus, args.univ, year=args.year, semester=args.semester)
            print_json([faculty.to_dict() for faculty in faculties])
            return 0
        if args.command == "courses":
            courses = service.get_courses(args.year, args.semester, args.campus, args.univ, args.faculty)
            print_json([course.to_dict() for course in courses])
            return 0
        if args.command == "export":
            outdir = Path(args.outdir) if args.outdir else settings.output_dir
            result = export_dongguk_courses(
                service,
                year=args.year,
                semester=args.semester,
                outdir=outdir,
                campus_code=args.campus,
                univ_code=args.univ,
                faculty_code=args.faculty,
                batch_index=args.batch_index,
                batch_size=args.batch_size,
            )
            print_json(result)
            return 0

    parser.error(f"Unsupported command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
