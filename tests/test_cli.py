from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from k_univ_mcp import cli
from k_univ_mcp.browser_bootstrap import BrowserBootstrapError
from k_univ_mcp.export_runtime import ExportFailureDiagnostic, ExportProgress
from k_univ_mcp.providers.dongguk.client import DonggukError
from k_univ_mcp.providers.yonsei.client import YonseiAuthenticationError


@dataclass
class FailingYonseiService:
    error: Exception

    def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str):
        raise self.error


def test_cli_prints_actionable_hint_for_missing_yonsei_cookie(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "create_yonsei_service", lambda settings: FailingYonseiService(
        ValueError("Yonsei live API access requires YONSEI_COOKIE. Seeded campus and college discovery can work without it.")
    ))

    exit_code = cli.main([
        "yonsei",
        "departments",
        "--campus",
        "sinchon-undergraduate",
        "--college",
        "s1103",
        "--year",
        "2026",
        "--semester",
        "1",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "YONSEI_COOKIE" in captured.err
    assert "auto-attempt browser bootstrap" in captured.err


def test_cli_prints_actionable_hint_for_yonsei_auth_failures(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "create_yonsei_service", lambda settings: FailingYonseiService(
        YonseiAuthenticationError("session may be expired")
    ))

    exit_code = cli.main([
        "yonsei",
        "departments",
        "--campus",
        "sinchon-undergraduate",
        "--college",
        "s1103",
        "--year",
        "2026",
        "--semester",
        "1",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Yonsei request failed" in captured.err
    assert "auto-attempt browser bootstrap" in captured.err


def test_yonsei_help_mentions_live_session_requirement(capsys) -> None:
    try:
        cli.main(["yonsei", "--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "usage: k-univ-mcp yonsei" in captured.out
    assert "YONSEI_COOKIE" in captured.out
    assert "browser bootstrap" in captured.out


def test_yonsei_doctor_reports_cli_auto_bootstrap_when_cookie_is_missing(monkeypatch, capsys) -> None:
    monkeypatch.delenv("YONSEI_COOKIE", raising=False)
    monkeypatch.setenv("ENABLE_BROWSER_BOOTSTRAP", "false")
    monkeypatch.setenv("BROWSER_BOOTSTRAP_ON_START", "false")

    exit_code = cli.main(["yonsei", "doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "yonsei"
    assert payload["ready"] is True
    assert payload["checks"]["YONSEI_COOKIE"] is False
    assert payload["checks"]["ENABLE_BROWSER_BOOTSTRAP"] is True
    assert payload["checks"]["BROWSER_BOOTSTRAP_ON_START"] is True
    assert any("auto-attempt browser bootstrap" in hint for hint in payload["hints"])


def test_yonsei_bootstrap_prints_cookie_payload(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_bootstrap_yonsei_session", lambda settings: {
        "provider": "yonsei",
        "browser": "headless",
        "cookie_header": "JSESSIONID=test",
        "hint": "Export this as YONSEI_COOKIE.",
    })

    exit_code = cli.main(["yonsei", "bootstrap"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "yonsei"
    assert payload["cookie_header"] == "JSESSIONID=test"


def test_yonsei_bootstrap_can_export_shell(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_bootstrap_yonsei_session", lambda settings: {
        "provider": "yonsei",
        "browser": "headless",
        "cookie_header": "JSESSIONID=test; NetFunnel_ID=abc",
        "hint": "Export this as YONSEI_COOKIE.",
    })

    exit_code = cli.main(["yonsei", "bootstrap", "--export-shell"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "export YONSEI_COOKIE='JSESSIONID=test; NetFunnel_ID=abc'" in captured.out


def test_yonsei_bootstrap_can_write_env_file(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_bootstrap_yonsei_session", lambda settings: {
        "provider": "yonsei",
        "browser": "headless",
        "cookie_header": "JSESSIONID=test",
        "hint": "Export this as YONSEI_COOKIE.",
    })
    env_path = tmp_path / ".env"
    env_path.write_text("FOO=bar\nYONSEI_COOKIE=old\n", encoding="utf-8")

    exit_code = cli.main(["yonsei", "bootstrap", "--write-env", str(env_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["written_env_path"] == str(env_path)
    assert payload["written_keys"] == ["YONSEI_COOKIE"]
    assert env_path.read_text(encoding="utf-8") == "FOO=bar\nYONSEI_COOKIE=JSESSIONID=test\n"


def test_yonsei_live_commands_enable_bootstrap_defaults_without_env(monkeypatch) -> None:
    captured: dict[str, object] = {}

    @dataclass
    class RecordingService:
        def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str):
            return []

    def fake_create_yonsei_service(settings):
        captured["enable_browser_bootstrap"] = settings.enable_browser_bootstrap
        captured["browser_bootstrap_on_start"] = settings.browser_bootstrap_on_start
        return RecordingService()

    monkeypatch.setattr(cli, "create_yonsei_service", fake_create_yonsei_service)
    monkeypatch.delenv("YONSEI_COOKIE", raising=False)
    monkeypatch.setenv("ENABLE_BROWSER_BOOTSTRAP", "false")
    monkeypatch.setenv("BROWSER_BOOTSTRAP_ON_START", "false")

    exit_code = cli.main([
        "yonsei",
        "departments",
        "--campus",
        "sinchon-undergraduate",
        "--college",
        "s1103",
        "--year",
        "2026",
        "--semester",
        "1",
    ])

    assert exit_code == 0
    assert captured["enable_browser_bootstrap"] is True
    assert captured["browser_bootstrap_on_start"] is True


def test_cli_prints_actionable_hint_for_bootstrap_failures(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_bootstrap_yonsei_session", lambda settings: (_ for _ in ()).throw(BrowserBootstrapError("missing chromium")))

    exit_code = cli.main(["yonsei", "bootstrap"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Yonsei browser bootstrap failed" in captured.err
    assert "Playwright Chromium" in captured.err


def test_dongguk_doctor_suggests_bootstrap_when_no_cookie(monkeypatch, capsys) -> None:
    monkeypatch.delenv("DONGGUK_COOKIE", raising=False)
    monkeypatch.delenv("DONGGUK_SEOUL_COOKIE", raising=False)
    monkeypatch.delenv("DONGGUK_WISE_COOKIE", raising=False)
    monkeypatch.setenv("DONGGUK_ENABLE_BROWSER_BOOTSTRAP", "false")

    exit_code = cli.main(["dongguk", "doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "dongguk"
    assert payload["ready"] is False
    assert any("dongguk bootstrap" in hint for hint in payload["hints"])


def test_gachon_doctor_reports_zero_config_ready(monkeypatch, capsys) -> None:
    monkeypatch.delenv("GACHON_COOKIE", raising=False)

    exit_code = cli.main(["gachon", "doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "gachon"
    assert payload["ready"] is True
    assert any("auto-acquire WMONID" in hint for hint in payload["hints"])


def test_hanyang_doctor_reports_zero_config_ready(monkeypatch, capsys) -> None:
    monkeypatch.delenv("HANYANG_COOKIE", raising=False)
    monkeypatch.delenv("HANYANG_TK", raising=False)

    exit_code = cli.main(["hanyang", "doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "hanyang"
    assert payload["ready"] is True
    assert any("built-in defaults" in hint for hint in payload["hints"])


def test_myongji_doctor_reports_ready_without_special_runtime(monkeypatch, capsys) -> None:
    monkeypatch.delenv("MYONGJI_TIMEOUT", raising=False)

    exit_code = cli.main(["myongji", "doctor"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "myongji"
    assert payload["ready"] is True
    assert payload["hints"] == []


def test_myongji_export_uses_standard_provider_flow(monkeypatch, capsys, tmp_path: Path) -> None:
    class RecordingService:
        def collect_courses(
            self,
            *,
            year: str,
            semester: str,
            campus_code=None,
            college_code=None,
            department_code=None,
            progress_callback=None,
            failure_callback=None,
        ):
            _ = (campus_code, college_code, department_code, failure_callback)
            assert progress_callback is not None
            progress_callback(ExportProgress(provider="myongji", current=1, total=1, label="2026 / 1"))
            return [{"provider": "myongji", "year": year, "semester_code": semester, "semester_name": "1학기"}], []

    monkeypatch.setattr(cli, "create_myongji_service", lambda settings: RecordingService())
    monkeypatch.setattr(cli, "export_courses", lambda courses, outdir, stem, raw_payloads=None: [str(outdir / f"{stem}.json")])

    exit_code = cli.main([
        "myongji",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--campus",
        "inmun",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["row_count"] == 1
    assert "[loading.............]" in captured.err
    assert "[####################] 100%" in captured.err


def test_dongguk_bootstrap_prints_session_payload(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_bootstrap_dongguk_session", lambda settings: {
        "provider": "dongguk",
        "browser": "headless",
        "campuses": {"seoul": {"cookie_header": "JSESSIONID=test", "running_nana": "n", "running_main_open_key": "m", "running_login_iden_no": "i"}},
        "hint": "Use these values for Dongguk live requests.",
    })

    exit_code = cli.main(["dongguk", "bootstrap"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider"] == "dongguk"
    assert payload["campuses"]["seoul"]["cookie_header"] == "JSESSIONID=test"


def test_dongguk_bootstrap_can_write_env_file(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "_bootstrap_dongguk_session", lambda settings: {
        "provider": "dongguk",
        "browser": "headless",
        "campuses": {
            "seoul": {"cookie_header": "JSESSIONID=seoul", "running_nana": "n1", "running_main_open_key": "m1", "running_login_iden_no": "i1"},
            "wise": {"cookie_header": "JSESSIONID=wise", "running_nana": "n2", "running_main_open_key": "m2", "running_login_iden_no": "i2"},
        },
        "hint": "Use these values for Dongguk live requests.",
    })
    env_path = tmp_path / ".env"

    exit_code = cli.main(["dongguk", "bootstrap", "--write-env", str(env_path)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["written_keys"] == ["DONGGUK_SEOUL_COOKIE", "DONGGUK_WISE_COOKIE"]
    assert env_path.read_text(encoding="utf-8") == "DONGGUK_SEOUL_COOKIE=JSESSIONID=seoul\nDONGGUK_WISE_COOKIE=JSESSIONID=wise\n"


def test_cli_prints_actionable_hint_for_dongguk_runtime_failures(monkeypatch, capsys) -> None:
    @dataclass
    class FailingDonggukService:
        def get_departments(self, campus_code: str, college_code: str, *, year: str, semester: str):
            raise DonggukError("session expired")

    monkeypatch.setattr(cli, "create_dongguk_service", lambda settings: FailingDonggukService())

    exit_code = cli.main([
        "dongguk",
        "departments",
        "--campus",
        "seoul",
        "--college",
        "DS0312",
        "--year",
        "2026",
        "--semester",
        "1",
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Dongguk request failed" in captured.err
    assert "dongguk bootstrap" in captured.err


def test_all_help_mentions_batch_size_requirement(capsys) -> None:
    try:
        cli.main(["all", "--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "usage: k-univ-mcp all" in captured.out
    assert "--batch-size" in captured.out
    assert "Dongguk" in captured.out


def test_all_export_reuses_provider_exports(monkeypatch, capsys, tmp_path: Path) -> None:
    captured_yonsei_settings: dict[str, object] = {}
    export_calls: list[dict[str, object]] = []
    dongguk_calls: list[dict[str, object]] = []

    class RecordingService:
        def __init__(self, provider: str) -> None:
            self.provider = provider

        def collect_courses(
            self,
            *,
            year: str,
            semester: str,
            campus_code=None,
            college_code=None,
            department_code=None,
            progress_callback=None,
            failure_callback=None,
        ):
            _ = (campus_code, college_code, department_code, progress_callback, failure_callback)
            return [{"provider": self.provider, "year": year, "semester": semester}], []

    def fake_create_yonsei_service(settings):
        captured_yonsei_settings["enable_browser_bootstrap"] = settings.enable_browser_bootstrap
        captured_yonsei_settings["browser_bootstrap_on_start"] = settings.browser_bootstrap_on_start
        return RecordingService("yonsei")

    monkeypatch.setattr(cli, "create_yonsei_service", fake_create_yonsei_service)
    monkeypatch.setattr(cli, "create_dongguk_service", lambda settings: object())
    monkeypatch.setattr(cli, "create_gachon_service", lambda settings: RecordingService("gachon"))
    monkeypatch.setattr(cli, "create_inha_service", lambda: RecordingService("inha"))
    monkeypatch.setattr(cli, "create_myongji_service", lambda settings: RecordingService("myongji"))
    monkeypatch.setattr(cli, "create_sungshin_service", lambda settings: RecordingService("sungshin"))
    monkeypatch.setattr(cli, "create_soongsil_service", lambda settings: RecordingService("soongsil"))
    monkeypatch.setattr(cli, "create_hanyang_service", lambda settings: RecordingService("hanyang"))
    monkeypatch.setattr(
        cli,
        "export_courses",
        lambda courses, outdir, stem, raw_payloads=None: export_calls.append({
            "outdir": str(outdir),
            "stem": stem,
            "row_count": len(courses),
        }) or [str(outdir / f"{stem}.json")],
    )
    monkeypatch.setattr(
        cli,
        "export_dongguk_courses",
        lambda service, **kwargs: dongguk_calls.append(kwargs) or {
            "artifacts": [str(kwargs["outdir"] / "dongguk_2026_1.json")],
            "row_count": 3,
            "batch_size": kwargs["batch_size"],
        },
    )
    monkeypatch.delenv("YONSEI_COOKIE", raising=False)
    monkeypatch.setenv("ENABLE_BROWSER_BOOTSTRAP", "false")
    monkeypatch.setenv("BROWSER_BOOTSTRAP_ON_START", "false")

    exit_code = cli.main([
        "all",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--batch-size",
        "20",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["provider_count"] == 8
    assert payload["row_count"] == 10
    assert list(payload["providers"].keys()) == [
        "yonsei",
        "dongguk",
        "gachon",
        "inha",
        "sungshin",
        "soongsil",
        "hanyang",
        "myongji",
    ]
    assert len(export_calls) == 7
    assert [call["stem"] for call in export_calls] == [
        "yonsei_2026_1",
        "gachon_2026_1",
        "inha_2026_1",
        "sungshin_2026_1",
        "soongsil_2026_1",
        "hanyang_2026_1",
        "myongji_2026_1",
    ]
    assert [call["outdir"] for call in export_calls] == [
        str(tmp_path / "yonsei"),
        str(tmp_path / "gachon"),
        str(tmp_path / "inha"),
        str(tmp_path / "sungshin"),
        str(tmp_path / "soongsil"),
        str(tmp_path / "hanyang"),
        str(tmp_path / "myongji"),
    ]
    assert "yonsei   [loading.............]" in captured.err
    assert "dongguk  [loading.............]" in captured.err
    assert len(dongguk_calls) == 1
    assert dongguk_calls[0]["year"] == "2026"
    assert dongguk_calls[0]["semester"] == "1"
    assert dongguk_calls[0]["outdir"] == tmp_path / "dongguk"
    assert dongguk_calls[0]["campus_code"] is None
    assert dongguk_calls[0]["college_code"] is None
    assert dongguk_calls[0]["department_code"] is None
    assert dongguk_calls[0]["batch_index"] is None
    assert dongguk_calls[0]["batch_size"] == 20
    assert callable(dongguk_calls[0]["progress_callback"])
    assert callable(dongguk_calls[0]["failure_callback"])
    assert captured_yonsei_settings["enable_browser_bootstrap"] is True
    assert captured_yonsei_settings["browser_bootstrap_on_start"] is True


def test_all_export_rejects_non_positive_batch_size_before_running_providers(monkeypatch, capsys, tmp_path: Path) -> None:
    provider_called = False

    def fail_if_called(settings):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("provider should not be created when batch size is invalid")

    monkeypatch.setattr(cli, "create_yonsei_service", fail_if_called)

    exit_code = cli.main([
        "all",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--batch-size",
        "0",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert provider_called is False
    assert "positive batch_size" in captured.err


def test_all_export_surfaces_provider_context_on_failure(monkeypatch, capsys, tmp_path: Path) -> None:
    class RecordingService:
        def __init__(self, provider: str) -> None:
            self.provider = provider

        def collect_courses(
            self,
            *,
            year: str,
            semester: str,
            campus_code=None,
            college_code=None,
            department_code=None,
            progress_callback=None,
            failure_callback=None,
        ):
            _ = (campus_code, college_code, department_code, progress_callback, failure_callback)
            return [{"provider": self.provider, "year": year, "semester": semester}], []

    monkeypatch.setattr(cli, "create_yonsei_service", lambda settings: RecordingService("yonsei"))
    monkeypatch.setattr(cli, "create_dongguk_service", lambda settings: object())
    monkeypatch.setattr(cli, "export_courses", lambda courses, outdir, stem, raw_payloads=None: [str(outdir / f"{stem}.json")])
    monkeypatch.setattr(
        cli,
        "export_dongguk_courses",
        lambda service, **kwargs: (_ for _ in ()).throw(ValueError("Dongguk export failed")),
    )

    exit_code = cli.main([
        "all",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--batch-size",
        "20",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "[dongguk] Dongguk export failed" in captured.err



def test_single_provider_export_prints_progress_bar_to_stderr(monkeypatch, capsys, tmp_path: Path) -> None:
    events: list[str] = []

    class RecordingService:
        def collect_courses(
            self,
            *,
            year: str,
            semester: str,
            campus_code=None,
            college_code=None,
            department_code=None,
            progress_callback=None,
            failure_callback=None,
        ):
            _ = (campus_code, college_code, department_code, failure_callback)
            events.append("collect")
            assert progress_callback is not None
            progress_callback(ExportProgress(provider="inha", current=1, total=2, label="step-1"))
            progress_callback(ExportProgress(provider="inha", current=2, total=2, label="step-2"))
            return [{"provider": "inha", "year": year, "semester": semester}], []

    def fake_create_inha_service() -> RecordingService:
        events.append("create")
        return RecordingService()

    monkeypatch.setattr(cli, "create_inha_service", fake_create_inha_service)
    monkeypatch.setattr(cli, "export_courses", lambda courses, outdir, stem, raw_payloads=None: [str(outdir / f"{stem}.json")])

    exit_code = cli.main([
        "inha",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert events == ["create", "collect"]
    assert "inha" in captured.err
    assert "[loading.............]" in captured.err
    assert captured.err.index("[loading.............]") < captured.err.index("[##########..........]  50%")
    assert "[##########..........]  50%" in captured.err
    assert "[####################] 100%" in captured.err


def test_single_provider_export_logs_failure_context_to_stderr(monkeypatch, capsys, tmp_path: Path) -> None:
    class FailingService:
        def collect_courses(
            self,
            *,
            year: str,
            semester: str,
            campus_code=None,
            college_code=None,
            department_code=None,
            progress_callback=None,
            failure_callback=None,
        ):
            _ = (year, semester, progress_callback)
            assert failure_callback is not None
            failure_callback(
                ExportFailureDiagnostic(
                    provider="inha",
                    stage="collect_courses",
                    error_type="RuntimeError",
                    message="department fetch failed",
                    year="2026",
                    semester="1",
                    campus_code="yonghyeon",
                    college_code="dept",
                    department_code="D001",
                )
            )
            raise RuntimeError("department fetch failed")

    monkeypatch.setattr(cli, "create_inha_service", lambda: FailingService())

    exit_code = cli.main([
        "inha",
        "export",
        "--year",
        "2026",
        "--semester",
        "1",
        "--outdir",
        str(tmp_path),
    ])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "[export-error] inha / collect_courses / yonghyeon / dept / D001: RuntimeError: department fetch failed" in captured.err
