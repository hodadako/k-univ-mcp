from __future__ import annotations

import argparse
import shlex
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from k_univ_mcp.browser_bootstrap import BrowserBootstrapError, BrowserBootstrapSettings, BrowserBootstrapTarget, BrowserSessionBootstrap
from k_univ_mcp.export_runtime import ExportFailureDiagnostic, ExportProgress
from k_univ_mcp.exporter import export_courses, print_json, resolve_provider_outdir
from k_univ_mcp.providers.dongguk import create_dongguk_service, export_dongguk_courses, require_dongguk_export_batch_size
from k_univ_mcp.providers.dongguk.bootstrap import DonggukBrowserBootstrap
from k_univ_mcp.providers.dongguk.client import DonggukError
from k_univ_mcp.providers.dongguk.service import DONGGUK_CAMPUS_ADAPTERS, DONGGUK_REQUIRED_BROWSER_COOKIES
from k_univ_mcp.providers.gachon import create_gachon_service
from k_univ_mcp.providers.gachon.client import GachonError
from k_univ_mcp.providers.hanyang import create_hanyang_service
from k_univ_mcp.providers.hanyang.client import HanyangError
from k_univ_mcp.providers.inha import create_inha_service
from k_univ_mcp.providers.soongsil import create_soongsil_service
from k_univ_mcp.providers.sungshin import create_sungshin_service
from k_univ_mcp.providers.yonsei import create_yonsei_service
from k_univ_mcp.providers.yonsei.client import YonseiError
from k_univ_mcp.providers.yonsei.service import YONSEI_CLICK_SELECTOR, YONSEI_READY_SELECTOR, YONSEI_REQUIRED_BROWSER_COOKIES
from k_univ_mcp.semester import semester_help_text
from k_univ_mcp.settings import AppSettings


ProviderFactory = Callable[[AppSettings], Any]

SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "yonsei",
    "dongguk",
    "gachon",
    "inha",
    "sungshin",
    "soongsil",
    "hanyang",
)


def _provider_factories() -> dict[str, ProviderFactory]:
    return {
        "yonsei": create_yonsei_service,
        "dongguk": create_dongguk_service,
        "gachon": create_gachon_service,
        "inha": lambda _settings: create_inha_service(),
        "sungshin": create_sungshin_service,
        "soongsil": create_soongsil_service,
        "hanyang": create_hanyang_service,
    }


PROVIDER_HELP_TEXT: dict[str, str] = {
    "yonsei": (
        "Yonsei campuses/colleges can work without a live session, but departments, courses, export, and bootstrap "
        "depend on YONSEI_COOKIE or browser bootstrap."
    ),
    "dongguk": (
        "Dongguk commands usually require browser bootstrap-backed session state; use 'bootstrap' to acquire it, "
        "and remember that export requires --batch-size."
    ),
    "gachon": "Gachon CLI commands work zero-config by default and auto-acquire WMONID when needed; GACHON_COOKIE is optional for session overrides.",
    "hanyang": "Hanyang CLI commands work with the built-in defaults; HANYANG_COOKIE and HANYANG_TK are optional overrides when you need a specific session.",
}


class _CliProgressReporter:
    def __init__(self) -> None:
        self._active = False

    @staticmethod
    def _render_bar(current: int, total: int, width: int = 20) -> str:
        if total <= 0:
            filled = width
        else:
            filled = min(width, round((current / total) * width))
        return "#" * filled + "." * (width - filled)

    @staticmethod
    def _render_loading_bar(width: int = 20) -> str:
        loading = "loading"
        return loading + "." * (width - len(loading))

    @staticmethod
    def _percent(current: int, total: int) -> int:
        if total <= 0:
            return 100
        return max(0, min(100, round((current / total) * 100)))

    def emit_loading(self, provider: str) -> None:
        print(
            f"\r{provider:<8} [{self._render_loading_bar()}]",
            end="",
            file=sys.stderr,
            flush=True,
        )
        self._active = True

    def emit_progress(self, progress: ExportProgress) -> None:
        bar = self._render_bar(progress.current, progress.total)
        percent = self._percent(progress.current, progress.total)
        print(
            f"\r{progress.provider:<8} [{bar}] {percent:3d}%",
            end="",
            file=sys.stderr,
            flush=True,
        )
        self._active = True

    def emit_failure(self, diagnostic: ExportFailureDiagnostic) -> None:
        self.finish()
        context_parts = [
            diagnostic.provider,
            diagnostic.stage,
            diagnostic.campus_code,
            diagnostic.college_code,
            diagnostic.department_code,
        ]
        if diagnostic.batch_index is not None:
            context_parts.append(f"batch={diagnostic.batch_index}")
        context = " / ".join(part for part in context_parts if part)
        print(
            f"[export-error] {context}: {diagnostic.error_type}: {diagnostic.message}",
            file=sys.stderr,
        )

    def finish(self) -> None:
        if self._active:
            print(file=sys.stderr, flush=True)
            self._active = False


def _add_common_provider_commands(
    provider_parser: argparse.ArgumentParser,
    *,
    provider_label: str,
    include_batch_args: bool = False,
) -> None:
    commands = provider_parser.add_subparsers(dest="command", required=True)

    campuses = commands.add_parser("campuses", help=f"List {provider_label} campuses")
    campuses.add_argument("--year", required=True)
    campuses.add_argument("--semester", required=True, help=semester_help_text())

    colleges = commands.add_parser("colleges", aliases=["universities"], help=f"List {provider_label} colleges for a campus")
    colleges.add_argument("--campus", required=True)
    colleges.add_argument("--year", required=True)
    colleges.add_argument("--semester", required=True, help=semester_help_text())

    departments = commands.add_parser(
        "departments",
        aliases=["faculties"],
        help=f"List {provider_label} departments for a college",
    )
    departments.add_argument("--campus", required=True)
    departments.add_argument("--college", "--univ", dest="college", required=True)
    departments.add_argument("--year", required=True)
    departments.add_argument("--semester", required=True, help=semester_help_text())

    courses = commands.add_parser("courses", help=f"List {provider_label} courses for a department")
    courses.add_argument("--year", required=True)
    courses.add_argument("--semester", required=True, help=semester_help_text())
    courses.add_argument("--campus", required=True)
    courses.add_argument("--college", "--univ", dest="college", required=True)
    courses.add_argument("--department", "--faculty", dest="department", required=True)

    export = commands.add_parser("export", help=f"Export {provider_label} courses")
    export.add_argument("--year", required=True)
    export.add_argument("--semester", required=True, help=semester_help_text())
    export.add_argument("--campus")
    export.add_argument("--college", "--univ", dest="college")
    export.add_argument("--department", "--faculty", dest="department")
    export.add_argument("--outdir", default=None)
    if include_batch_args:
        export.add_argument("--batch-index", type=int, default=None)
        export.add_argument("--batch-size", type=int, default=None)

    commands.add_parser("doctor", help=f"Check {provider_label} CLI runtime prerequisites")
    bootstrap = commands.add_parser("bootstrap", help=f"Acquire a fresh {provider_label} session via browser bootstrap")
    output_group = bootstrap.add_mutually_exclusive_group()
    output_group.add_argument(
        "--write-env",
        nargs="?",
        const=".env",
        default=None,
        metavar="PATH",
        help="Write the bootstrap result into a .env-style file (default: .env).",
    )
    output_group.add_argument(
        "--export-shell",
        action="store_true",
        help="Print shell export commands instead of JSON.",
    )


def _add_all_provider_commands(provider_parser: argparse.ArgumentParser) -> None:
    commands = provider_parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export", help="Export courses for all supported providers")
    export.add_argument("--year", required=True)
    export.add_argument("--semester", required=True, help=semester_help_text())
    export.add_argument("--outdir", default=None)
    export.add_argument(
        "--batch-size",
        type=int,
        required=True,
        help="Batch size forwarded to Dongguk export; required because Dongguk all-school export is batched.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="k-univ-mcp", description="k-univ-mcp CLI")
    provider_parser = parser.add_subparsers(dest="provider", required=True)

    yonsei_parser = provider_parser.add_parser(
        "yonsei",
        help="Yonsei provider commands",
        description="Yonsei provider commands",
        epilog=PROVIDER_HELP_TEXT["yonsei"],
    )
    _add_common_provider_commands(yonsei_parser, provider_label="Yonsei")

    dongguk_parser = provider_parser.add_parser(
        "dongguk",
        help="Dongguk provider commands",
        description="Dongguk provider commands",
        epilog=PROVIDER_HELP_TEXT["dongguk"],
    )
    _add_common_provider_commands(
        dongguk_parser,
        provider_label="Dongguk",
        include_batch_args=True,
    )

    gachon_parser = provider_parser.add_parser(
        "gachon",
        help="Gachon provider commands",
        description="Gachon provider commands",
        epilog=PROVIDER_HELP_TEXT["gachon"],
    )
    _add_common_provider_commands(gachon_parser, provider_label="Gachon")
    _add_common_provider_commands(provider_parser.add_parser("inha", help="Inha provider commands"), provider_label="Inha")
    _add_common_provider_commands(provider_parser.add_parser("sungshin", help="Sungshin provider commands"), provider_label="Sungshin")
    _add_common_provider_commands(provider_parser.add_parser("soongsil", help="Soongsil provider commands"), provider_label="Soongsil")

    hanyang_parser = provider_parser.add_parser(
        "hanyang",
        help="Hanyang provider commands",
        description="Hanyang provider commands",
        epilog=PROVIDER_HELP_TEXT["hanyang"],
    )
    _add_common_provider_commands(hanyang_parser, provider_label="Hanyang")

    all_parser = provider_parser.add_parser(
        "all",
        help="All provider export commands",
        description="Export courses for all supported providers",
        epilog="Runs the existing provider export flow sequentially for every supported university. --batch-size is required because Dongguk export is batched.",
    )
    _add_all_provider_commands(all_parser)

    return parser


def _bootstrap_yonsei_session(settings: AppSettings) -> dict[str, Any]:
    bootstrap = BrowserSessionBootstrap(
        target=BrowserBootstrapTarget(
            entry_url=settings.yonsei_referer,
            required_cookie_names=YONSEI_REQUIRED_BROWSER_COOKIES,
            ready_selector=YONSEI_READY_SELECTOR,
            click_selector=YONSEI_CLICK_SELECTOR,
        ),
        settings=BrowserBootstrapSettings(
            enabled=True,
            browser=settings.browser,
            timeout_ms=settings.browser_bootstrap_timeout_ms,
            ready_selector_override=settings.browser_ready_selector,
            click_selector_override=settings.browser_click_selector,
            auto_install_browser=settings.auto_install_playwright_browser,
        ),
    )
    cookie_header = bootstrap.resolve_cookie_header()
    return {
        "provider": "yonsei",
        "browser": settings.browser,
        "cookie_header": cookie_header,
        "hint": "Export this as YONSEI_COOKIE or write it into .env for subsequent Yonsei live commands.",
    }


def _bootstrap_dongguk_session(settings: AppSettings) -> dict[str, Any]:
    session_states: dict[str, dict[str, str]] = {}
    for public_code, adapter in DONGGUK_CAMPUS_ADAPTERS.items():
        bootstrap = DonggukBrowserBootstrap(
            target=BrowserBootstrapTarget(
                entry_url=adapter.referer,
                required_cookie_names=DONGGUK_REQUIRED_BROWSER_COOKIES,
            ),
            settings=BrowserBootstrapSettings(
                enabled=True,
                browser=settings.browser,
                timeout_ms=settings.browser_bootstrap_timeout_ms,
                ready_selector_override=settings.browser_ready_selector,
                click_selector_override=settings.browser_click_selector,
                auto_install_browser=settings.auto_install_playwright_browser,
            ),
        )
        state = bootstrap.resolve_session_state()
        session_states[public_code] = {
            "cookie_header": state.cookie_header,
            "running_nana": state.running_nana,
            "running_main_open_key": state.running_main_open_key,
            "running_login_iden_no": state.running_login_iden_no,
        }
    return {
        "provider": "dongguk",
        "browser": settings.browser,
        "campuses": session_states,
        "hint": "Use these values to populate DONGGUK_COOKIE or campus-specific cookies, and preserve the runtime fields for live Dongguk requests.",
    }


def _bootstrap_env_map(payload: dict[str, Any]) -> dict[str, str]:
    provider = payload.get("provider")
    if provider == "yonsei":
        cookie_header = payload.get("cookie_header")
        return {"YONSEI_COOKIE": cookie_header} if isinstance(cookie_header, str) and cookie_header else {}

    if provider == "dongguk":
        campuses = payload.get("campuses")
        env_map: dict[str, str] = {}
        if isinstance(campuses, dict):
            seoul = campuses.get("seoul")
            if isinstance(seoul, dict) and isinstance(seoul.get("cookie_header"), str) and seoul.get("cookie_header"):
                env_map["DONGGUK_SEOUL_COOKIE"] = seoul["cookie_header"]
            wise = campuses.get("wise")
            if isinstance(wise, dict) and isinstance(wise.get("cookie_header"), str) and wise.get("cookie_header"):
                env_map["DONGGUK_WISE_COOKIE"] = wise["cookie_header"]
        return env_map

    return {}


def _render_shell_exports(env_map: dict[str, str]) -> str:
    return "\n".join(f"export {key}={shlex.quote(value)}" for key, value in env_map.items())


def _write_env_file(path: Path, env_map: dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(env_map)
    updated_lines: list[str] = []
    for line in existing_lines:
        if "=" not in line or line.lstrip().startswith("#"):
            updated_lines.append(line)
            continue
        key, _value = line.split("=", 1)
        stripped_key = key.strip()
        if stripped_key in remaining:
            updated_lines.append(f"{stripped_key}={remaining.pop(stripped_key)}")
        else:
            updated_lines.append(line)
    for key, value in remaining.items():
        updated_lines.append(f"{key}={value}")
    content = "\n".join(updated_lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _emit_bootstrap_result(payload: dict[str, Any], args: argparse.Namespace) -> None:
    env_map = _bootstrap_env_map(payload)
    if args.export_shell:
        print(_render_shell_exports(env_map))
        return
    if args.write_env:
        output_path = Path(args.write_env)
        _write_env_file(output_path, env_map)
        print_json({
            "provider": payload.get("provider"),
            "written_env_path": str(output_path),
            "written_keys": sorted(env_map.keys()),
            "bootstrap": payload,
        })
        return
    print_json(payload)


def _uses_live_session(provider: str, command: str) -> bool:
    if provider == "yonsei":
        return command in {"departments", "courses", "export", "bootstrap"}
    return False


def _effective_cli_settings(settings: AppSettings, args: argparse.Namespace) -> AppSettings:
    if args.provider == "yonsei" and _uses_live_session(args.provider, args.command) and not settings.yonsei_cookie:
        return replace(
            settings,
            enable_browser_bootstrap=True,
            browser_bootstrap_on_start=True,
        )
    return settings


def _doctor_payload(provider: str, settings: AppSettings) -> dict[str, Any]:
    if provider == "yonsei":
        has_cookie = bool(settings.yonsei_cookie)
        bootstrap_enabled = settings.enable_browser_bootstrap or not has_cookie
        warmup_enabled = settings.browser_bootstrap_on_start or not has_cookie
        ready = has_cookie or (bootstrap_enabled and warmup_enabled)
        hints = []
        if not has_cookie:
            hints.append("CLI live Yonsei commands will auto-attempt browser bootstrap, typically in headless mode by default.")
            hints.append("Run 'k-univ-mcp yonsei bootstrap' if you want to inspect or persist the fresh session explicitly.")
        return {
            "provider": provider,
            "ready": ready,
            "checks": {
                "YONSEI_COOKIE": has_cookie,
                "ENABLE_BROWSER_BOOTSTRAP": bootstrap_enabled,
                "BROWSER_BOOTSTRAP_ON_START": warmup_enabled,
            },
            "hints": hints,
        }

    if provider == "dongguk":
        has_cookie = bool(settings.dongguk_cookie or settings.dongguk_seoul_cookie or settings.dongguk_wise_cookie)
        bootstrap_enabled = settings.dongguk_enable_browser_bootstrap
        hints: list[str] = []
        if not has_cookie:
            hints.append("Run 'k-univ-mcp dongguk bootstrap' to acquire fresh Dongguk session state for Seoul and WISE.")
        if not bootstrap_enabled:
            hints.append("Enable DONGGUK_ENABLE_BROWSER_BOOTSTRAP=true if you want the CLI to refresh Dongguk session state automatically.")
        return {
            "provider": provider,
            "ready": has_cookie or bootstrap_enabled,
            "checks": {
                "DONGGUK_COOKIE": has_cookie,
                "DONGGUK_ENABLE_BROWSER_BOOTSTRAP": bootstrap_enabled,
            },
            "hints": hints,
        }

    if provider == "gachon":
        has_cookie = bool(settings.gachon_cookie)
        return {
            "provider": provider,
            "ready": True,
            "checks": {"GACHON_COOKIE": has_cookie},
            "hints": [
                "Gachon CLI commands auto-acquire WMONID when needed; GACHON_COOKIE is only an optional override."
            ],
        }

    if provider == "soongsil":
        return {
            "provider": provider,
            "ready": True,
            "checks": {"BROWSER": settings.browser},
            "hints": [
                "Soongsil uses Playwright-driven collection; if it fails, install Chromium with 'python -m playwright install chromium'."
            ],
        }

    if provider == "hanyang":
        has_cookie = bool(settings.hanyang_cookie)
        has_token = bool(settings.hanyang_tk)
        return {
            "provider": provider,
            "ready": True,
            "checks": {
                "HANYANG_COOKIE": has_cookie,
                "HANYANG_TK": has_token,
            },
            "hints": [
                "Hanyang CLI commands work with built-in defaults; HANYANG_COOKIE and HANYANG_TK are optional overrides when needed."
            ],
        }

    return {
        "provider": provider,
        "ready": True,
        "checks": {},
        "hints": [],
    }


def _print_catalog(service: Any, settings: AppSettings, args: argparse.Namespace) -> int:
    if args.command == "doctor":
        print_json(_doctor_payload(args.provider, settings))
        return 0
    if args.command == "bootstrap" and args.provider == "yonsei":
        _emit_bootstrap_result(_bootstrap_yonsei_session(settings), args)
        return 0
    if args.command == "bootstrap" and args.provider == "dongguk":
        _emit_bootstrap_result(_bootstrap_dongguk_session(settings), args)
        return 0
    if args.command == "bootstrap":
        raise ValueError(f"{args.provider} does not support an explicit bootstrap command.")
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
    base_outdir = Path(args.outdir) if args.outdir else settings.output_dir
    outdir = resolve_provider_outdir(base_outdir, args.provider)
    stem = f"{args.provider}_{args.year}_{args.semester}"
    artifacts = export_courses(courses, outdir, stem, raw_payloads=raw_payloads)
    print_json({"artifacts": artifacts, "row_count": len(courses)})
    return 0


def _build_provider_args(args: argparse.Namespace, provider: str) -> argparse.Namespace:
    provider_args = argparse.Namespace(**vars(args))
    provider_args.provider = provider
    provider_args.campus = getattr(provider_args, "campus", None)
    provider_args.college = getattr(provider_args, "college", None)
    provider_args.department = getattr(provider_args, "department", None)
    provider_args.batch_index = getattr(provider_args, "batch_index", None)
    provider_args.batch_size = getattr(provider_args, "batch_size", None)
    return provider_args


def _create_provider_service(provider: str, settings: AppSettings, args: argparse.Namespace) -> Any:
    provider_args = _build_provider_args(args, provider)
    effective_settings = _effective_cli_settings(settings, provider_args)
    return _provider_factories()[provider](effective_settings)


def _run_single_provider_export(
    provider: str,
    settings: AppSettings,
    args: argparse.Namespace,
    *,
    reporter: _CliProgressReporter | None = None,
) -> dict[str, Any]:
    provider_args = _build_provider_args(args, provider)
    if reporter is not None:
        reporter.emit_loading(provider)
    service = _create_provider_service(provider, settings, provider_args)
    progress_callback = reporter.emit_progress if reporter is not None else None
    failure_callback = reporter.emit_failure if reporter is not None else None

    if provider == "dongguk":
        base_outdir = Path(provider_args.outdir) if provider_args.outdir else settings.output_dir
        outdir = resolve_provider_outdir(base_outdir, provider)
        return export_dongguk_courses(
            service,
            year=provider_args.year,
            semester=provider_args.semester,
            outdir=outdir,
            campus_code=provider_args.campus,
            college_code=provider_args.college,
            department_code=provider_args.department,
            batch_index=provider_args.batch_index,
            batch_size=provider_args.batch_size,
            progress_callback=progress_callback,
            failure_callback=failure_callback,
        )

    courses, raw_payloads = service.collect_courses(
        year=provider_args.year,
        semester=provider_args.semester,
        campus_code=provider_args.campus,
        college_code=provider_args.college,
        department_code=provider_args.department,
        progress_callback=progress_callback,
        failure_callback=failure_callback,
    )
    base_outdir = Path(provider_args.outdir) if provider_args.outdir else settings.output_dir
    outdir = resolve_provider_outdir(base_outdir, provider)
    stem = f"{provider}_{provider_args.year}_{provider_args.semester}"
    artifacts = export_courses(courses, outdir, stem, raw_payloads=raw_payloads)
    return {"artifacts": artifacts, "row_count": len(courses)}


def _run_all_export(settings: AppSettings, args: argparse.Namespace) -> int:
    require_dongguk_export_batch_size(args.batch_size)

    reporter = _CliProgressReporter()
    provider_results: dict[str, dict[str, Any]] = {}
    total_rows = 0

    for provider in SUPPORTED_PROVIDERS:
        try:
            result = _run_single_provider_export(provider, settings, args, reporter=reporter)
        except (ValueError, RuntimeError, BrowserBootstrapError, YonseiError, DonggukError, GachonError, HanyangError) as exc:
            raise ValueError(f"[{provider}] {_format_runtime_error(provider, exc)}") from exc
        finally:
            reporter.finish()
        provider_results[provider] = result
        total_rows += int(result.get("row_count", 0))

    print_json({
        "provider_count": len(provider_results),
        "providers": provider_results,
        "row_count": total_rows,
    })
    return 0


def _format_runtime_error(provider: str, exc: Exception) -> str:
    message = str(exc)

    if provider == "yonsei":
        if "YONSEI_COOKIE" in message:
            return (
                f"{message}\n"
                "Hint: CLI live Yonsei commands now auto-attempt browser bootstrap. If that still fails, run 'k-univ-mcp yonsei bootstrap' "
                "or ensure Playwright Chromium is installed."
            )
        if isinstance(exc, YonseiError):
            return (
                f"Yonsei request failed: {message}\n"
                "Hint: CLI live Yonsei commands auto-attempt browser bootstrap; if the issue persists, run 'k-univ-mcp yonsei bootstrap' or inspect Playwright/Chromium setup."
            )

    if provider == "yonsei" and isinstance(exc, BrowserBootstrapError):
        return (
            f"Yonsei browser bootstrap failed: {message}\n"
            "Hint: Ensure Playwright Chromium is installed. Live Yonsei CLI commands rely on this automatic bootstrap path when no cookie is configured."
        )

    if provider == "dongguk" and isinstance(exc, DonggukError):
        return (
            f"Dongguk request failed: {message}\n"
            "Hint: Check DONGGUK cookie/bootstrap settings or run 'k-univ-mcp dongguk bootstrap'. Dongguk often requires browser bootstrap-backed session state."
        )

    if provider == "gachon" and isinstance(exc, GachonError):
        return (
            f"Gachon request failed: {message}\n"
            "Hint: Refresh GACHON_COOKIE or retry with a fresh session."
        )

    if provider == "hanyang" and isinstance(exc, HanyangError):
        return (
            f"Hanyang request failed: {message}\n"
            "Hint: Check HANYANG_COOKIE and related session variables in your environment."
        )

    return message


def _run_provider_command(
    parser: argparse.ArgumentParser,
    settings: AppSettings,
    args: argparse.Namespace,
) -> int:
    if args.provider == "all":
        if args.command != "export":
            parser.error(f"Unsupported command: {args.command}")
        return _run_all_export(settings, args)

    effective_settings = _effective_cli_settings(settings, args)

    if args.command != "export":
        service = _provider_factories()[args.provider](effective_settings)
        printed = _print_catalog(service, effective_settings, args)
        if printed == 0:
            return 0
        parser.error(f"Unsupported command: {args.command}")

    reporter = _CliProgressReporter()
    try:
        result = _run_single_provider_export(args.provider, settings, args, reporter=reporter)
    finally:
        reporter.finish()
    print_json(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    try:
        return _run_provider_command(parser, settings, args)
    except (ValueError, RuntimeError, BrowserBootstrapError, YonseiError, DonggukError, GachonError, HanyangError) as exc:
        print(_format_runtime_error(args.provider, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
