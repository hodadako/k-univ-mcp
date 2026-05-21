from __future__ import annotations

from pathlib import Path
from typing import Any

from k_univ_mcp.exporter import export_courses
from k_univ_mcp.providers.dongguk import create_dongguk_service, export_dongguk_courses
from k_univ_mcp.providers.gachon import create_gachon_service
from k_univ_mcp.providers.inha import create_inha_service
from k_univ_mcp.providers.sungshin import create_sungshin_service
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.settings import AppSettings


def build_mcp_server(settings: AppSettings | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("The 'mcp' package is required to run the MCP server. Install project dependencies first.") from exc

    app_settings = settings or AppSettings.from_env()
    server = FastMCP("k-univ-mcp", json_response=True)

    yonsei_service = create_yonsei_service(app_settings)
    dongguk_service = create_dongguk_service(app_settings)
    gachon_service = create_gachon_service(app_settings)
    inha_service = create_inha_service()
    sungshin_service = create_sungshin_service(app_settings)

    @server.tool(name="yonsei_get_campuses")
    def yonsei_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in yonsei_service.get_campuses(year=year, semester=semester)]

    @server.tool(name="yonsei_get_universities")
    def yonsei_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [
            university.to_dict()
            for university in yonsei_service.get_universities(campus_code, year=year, semester=semester)
        ]

    @server.tool(name="yonsei_get_faculties")
    def yonsei_get_faculties(
        campus_code: str,
        univ_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [
            faculty.to_dict()
            for faculty in yonsei_service.get_faculties(campus_code, univ_code, year=year, semester=semester)
        ]

    @server.tool(name="yonsei_get_courses")
    def yonsei_get_courses(
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        return [
            course.to_dict()
            for course in yonsei_service.get_courses(year, semester, campus_code, univ_code, faculty_code)
        ]

    @server.tool(name="yonsei_export_courses")
    def yonsei_export_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> dict[str, Any]:
        courses, raw_payloads = yonsei_service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )
        artifacts = export_courses(courses, Path(outdir), f"yonsei_{year}_{semester}", raw_payloads=raw_payloads)
        return {"artifacts": artifacts, "row_count": len(courses)}

    @server.tool(name="dongguk_get_campuses")
    def dongguk_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in dongguk_service.get_campuses(year=year, semester=semester)]

    @server.tool(name="dongguk_get_universities")
    def dongguk_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [university.to_dict() for university in dongguk_service.get_universities(campus_code, year=year, semester=semester)]

    @server.tool(name="dongguk_get_faculties")
    def dongguk_get_faculties(
        campus_code: str,
        univ_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [faculty.to_dict() for faculty in dongguk_service.get_faculties(campus_code, univ_code, year=year, semester=semester)]

    @server.tool(name="dongguk_get_courses")
    def dongguk_get_courses(
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        return [course.to_dict() for course in dongguk_service.get_courses(year, semester, campus_code, univ_code, faculty_code)]

    @server.tool(name="dongguk_export_courses")
    def dongguk_export_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
        batch_index: int | None = None,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        return export_dongguk_courses(
            dongguk_service,
            year=year,
            semester=semester,
            outdir=Path(outdir),
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
            batch_index=batch_index,
            batch_size=batch_size,
        )

    @server.tool(name="gachon_get_campuses")
    def gachon_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in gachon_service.get_campuses(year=year, semester=semester)]

    @server.tool(name="gachon_get_universities")
    def gachon_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [university.to_dict() for university in gachon_service.get_universities(campus_code, year=year, semester=semester)]

    @server.tool(name="gachon_get_faculties")
    def gachon_get_faculties(
        campus_code: str,
        univ_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [faculty.to_dict() for faculty in gachon_service.get_faculties(campus_code, univ_code, year=year, semester=semester)]

    @server.tool(name="gachon_get_courses")
    def gachon_get_courses(
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        return [course.to_dict() for course in gachon_service.get_courses(year, semester, campus_code, univ_code, faculty_code)]

    @server.tool(name="gachon_export_courses")
    def gachon_export_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> dict[str, Any]:
        courses, raw_payloads = gachon_service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )
        artifacts = export_courses(courses, Path(outdir), f"gachon_{year}_{semester}", raw_payloads=raw_payloads)
        return {"artifacts": artifacts, "row_count": len(courses)}

    @server.tool(name="inha_get_campuses")
    def inha_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in inha_service.get_campuses(year=year, semester=semester)]

    @server.tool(name="inha_get_universities")
    def inha_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [university.to_dict() for university in inha_service.get_universities(campus_code, year=year, semester=semester)]

    @server.tool(name="inha_get_faculties")
    def inha_get_faculties(
        campus_code: str,
        univ_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [faculty.to_dict() for faculty in inha_service.get_faculties(campus_code, univ_code, year=year, semester=semester)]

    @server.tool(name="inha_get_courses")
    def inha_get_courses(
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        return [course.to_dict() for course in inha_service.get_courses(year, semester, campus_code, univ_code, faculty_code)]

    @server.tool(name="inha_export_courses")
    def inha_export_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> dict[str, Any]:
        courses, raw_payloads = inha_service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )
        artifacts = export_courses(courses, Path(outdir), f"inha_{year}_{semester}", raw_payloads=raw_payloads)
        return {"artifacts": artifacts, "row_count": len(courses)}

    @server.tool(name="sungshin_get_campuses")
    def sungshin_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in sungshin_service.get_campuses(year=year, semester=semester)]

    @server.tool(name="sungshin_get_universities")
    def sungshin_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [
            university.to_dict()
            for university in sungshin_service.get_universities(campus_code, year=year, semester=semester)
        ]

    @server.tool(name="sungshin_get_faculties")
    def sungshin_get_faculties(
        campus_code: str,
        univ_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [
            faculty.to_dict()
            for faculty in sungshin_service.get_faculties(campus_code, univ_code, year=year, semester=semester)
        ]

    @server.tool(name="sungshin_get_courses")
    def sungshin_get_courses(
        year: str,
        semester: str,
        campus_code: str,
        univ_code: str,
        faculty_code: str,
    ) -> list[dict[str, Any]]:
        return [
            course.to_dict()
            for course in sungshin_service.get_courses(year, semester, campus_code, univ_code, faculty_code)
        ]

    @server.tool(name="sungshin_export_courses")
    def sungshin_export_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        univ_code: str | None = None,
        faculty_code: str | None = None,
    ) -> dict[str, Any]:
        courses, raw_payloads = sungshin_service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )
        artifacts = export_courses(courses, Path(outdir), f"sungshin_{year}_{semester}", raw_payloads=raw_payloads)
        return {"artifacts": artifacts, "row_count": len(courses)}

    return server


def create_server(settings: AppSettings | None = None):
    return build_mcp_server(settings)


def main() -> None:
    settings = AppSettings.from_env()
    server = build_mcp_server(settings)
    server.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
