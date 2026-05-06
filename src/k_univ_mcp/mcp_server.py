from __future__ import annotations

from pathlib import Path
from typing import Any

from k_univ_mcp.exporter import export_courses, resolve_provider_outdir
from k_univ_mcp.providers.dongguk import create_dongguk_service, export_dongguk_courses
from k_univ_mcp.providers.gachon import create_gachon_service
from k_univ_mcp.providers.hanyang import create_hanyang_service
from k_univ_mcp.providers.inha import create_inha_service
from k_univ_mcp.providers.soongsil import create_soongsil_service
from k_univ_mcp.providers.sungshin import create_sungshin_service
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.settings import AppSettings


def _register_catalog_tools(server: Any, prefix: str, service: Any) -> None:
    @server.tool(name=f"{prefix}_get_campuses")
    def get_campuses(year: str, semester: str) -> list[dict[str, Any]]:
        return [campus.to_dict() for campus in service.get_campuses(year=year, semester=semester)]

    @server.tool(name=f"{prefix}_get_colleges")
    def get_colleges(campus_code: str, year: str, semester: str) -> list[dict[str, Any]]:
        return [college.to_dict() for college in service.get_colleges(campus_code, year=year, semester=semester)]

    @server.tool(name=f"{prefix}_get_departments")
    def get_departments(campus_code: str, college_code: str, year: str, semester: str) -> list[dict[str, Any]]:
        return [
            department.to_dict()
            for department in service.get_departments(
                campus_code,
                college_code,
                year=year,
                semester=semester,
            )
        ]

    @server.tool(name=f"{prefix}_get_courses")
    def get_courses(
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[dict[str, Any]]:
        return [
            course.to_dict()
            for course in service.get_courses(
                year,
                semester,
                campus_code,
                college_code,
                department_code,
            )
        ]


def _register_export_tool(server: Any, prefix: str, service: Any) -> None:
    @server.tool(name=f"{prefix}_export_courses")
    def export_provider_courses(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
    ) -> dict[str, Any]:
        courses, raw_payloads = service.collect_courses(
            year=year,
            semester=semester,
            campus_code=campus_code,
            college_code=college_code,
            department_code=department_code,
        )
        artifacts = export_courses(
            courses,
            resolve_provider_outdir(Path(outdir), prefix),
            f"{prefix}_{year}_{semester}",
            raw_payloads=raw_payloads,
        )
        return {"artifacts": artifacts, "row_count": len(courses)}


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
    soongsil_service = create_soongsil_service(app_settings)
    hanyang_service = create_hanyang_service(app_settings)

    for prefix, service in (
        ("yonsei", yonsei_service),
        ("dongguk", dongguk_service),
        ("gachon", gachon_service),
        ("inha", inha_service),
        ("sungshin", sungshin_service),
        ("soongsil", soongsil_service),
        ("hanyang", hanyang_service),
    ):
        _register_catalog_tools(server, prefix, service)

    _register_export_tool(server, "yonsei", yonsei_service)
    _register_export_tool(server, "gachon", gachon_service)
    _register_export_tool(server, "inha", inha_service)
    _register_export_tool(server, "sungshin", sungshin_service)
    _register_export_tool(server, "soongsil", soongsil_service)
    _register_export_tool(server, "hanyang", hanyang_service)

    @server.tool(name="dongguk_export_courses")
    def dongguk_export_courses_tool(
        year: str,
        semester: str,
        outdir: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
        batch_index: int | None = None,
        batch_size: int | None = None,
    ) -> dict[str, Any]:
        return export_dongguk_courses(
            dongguk_service,
            year=year,
            semester=semester,
            outdir=resolve_provider_outdir(Path(outdir), "dongguk"),
            campus_code=campus_code,
            college_code=college_code,
            department_code=department_code,
            batch_index=batch_index,
            batch_size=batch_size,
        )

    return server


def create_server(settings: AppSettings | None = None):
    return build_mcp_server(settings)


def main() -> None:
    settings = AppSettings.from_env()
    server = build_mcp_server(settings)
    server.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()
