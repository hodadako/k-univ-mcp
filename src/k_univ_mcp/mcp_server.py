from __future__ import annotations

from pathlib import Path
from typing import Any

from k_univ_mcp.exporter import export_courses
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.settings import AppSettings


def build_mcp_server(settings: AppSettings | None = None):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("The 'mcp' package is required to run the MCP server. Install project dependencies first.") from exc

    app_settings = settings or AppSettings.from_env()
    service = create_yonsei_service(app_settings)
    server = FastMCP("k-univ-mcp", json_response=True)

    @server.tool(name="yonsei_get_campuses")
    def yonsei_get_campuses(
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in service.get_campuses(year=year, semester=semester)]

    @server.tool(name="yonsei_get_universities")
    def yonsei_get_universities(
        campus_code: str,
        year: str,
        semester: str,
    ) -> list[dict[str, Any]]:
        return [
            university.to_dict()
            for university in service.get_universities(campus_code, year=year, semester=semester)
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
            for faculty in service.get_faculties(campus_code, univ_code, year=year, semester=semester)
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
            for course in service.get_courses(year, semester, campus_code, univ_code, faculty_code)
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
        courses, raw_payloads = service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            univ_code=univ_code,
            faculty_code=faculty_code,
        )
        artifacts = export_courses(courses, Path(outdir), f"yonsei_{year}_{semester}", raw_payloads=raw_payloads)
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
