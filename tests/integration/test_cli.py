"""Integration: CLI exit codes and harness report contracts (needs oracle)."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from bat2ps.cli import main as cli_main

NEEDS_ORACLE = pytest.mark.skipif(
    not (shutil.which("cmd") and (shutil.which("powershell") or shutil.which("pwsh"))),
    reason="needs cmd + powershell",
)


def _run_cli(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bat2ps.cli", *argv],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )


def test_convert_ok(tmp_path):
    bat = tmp_path / "ok.bat"
    bat.write_text("@echo off\necho hi\n", encoding="utf-8")
    out = tmp_path / "ok.ps1"
    assert cli_main(["convert", str(bat), "-o", str(out)]) == 0
    assert "Write-Output" in out.read_text(encoding="utf-8")


def test_convert_unsupported_exit_2(tmp_path, capsys):
    bat = tmp_path / "bad.bat"
    bat.write_text("wmic os get caption\n", encoding="utf-8")
    assert cli_main(["convert", str(bat)]) == 2


def test_convert_missing_file_exit_3():
    assert cli_main(["convert", "no-such-file.bat"]) == 3


def test_convert_unsupported_profile_exit_2(tmp_path):
    bat = tmp_path / "ok.bat"
    bat.write_text("@echo off\necho hi\n", encoding="utf-8")
    assert cli_main(["convert", str(bat), "--profile", "v9.9"]) == 2


def test_convert_invalid_utf8_exit_3(tmp_path):
    bat = tmp_path / "cp1252.bat"
    bat.write_bytes(b"@echo off\necho caf\xe9\n")
    assert cli_main(["convert", str(bat)]) == 3


def test_convert_unwritable_output_exit_3(tmp_path):
    bat = tmp_path / "ok.bat"
    bat.write_text("@echo off\necho hi\n", encoding="utf-8")
    out = tmp_path / "missing" / "ok.ps1"
    assert cli_main(["convert", str(bat), "-o", str(out)]) == 3


def test_convert_partial_unwritable_output_exit_3(tmp_path):
    bat = tmp_path / "bad.bat"
    bat.write_text("wmic os get caption\n", encoding="utf-8")
    out = tmp_path / "missing" / "bad.ps1"
    assert cli_main(["convert", str(bat), "-o", str(out), "--allow-partial"]) == 3


def test_verify_missing_against_exit_3(tmp_path):
    bat = tmp_path / "ok.bat"
    bat.write_text("@echo off\necho hi\n", encoding="utf-8")
    assert cli_main(["verify", str(bat), "--against", str(tmp_path / "missing.ps1")]) == 3


def test_harness_unwritable_json_exit_3(tmp_path):
    (tmp_path / "unsupported.bat").write_text("choice /c yn\n", encoding="utf-8")
    out = tmp_path / "missing" / "report.json"
    assert cli_main(["harness", str(tmp_path), "--json", str(out), "--quiet"]) == 3


def test_harness_missing_dir_exit_3():
    assert cli_main(["harness", "no-such-dir"]) == 3


@NEEDS_ORACLE
def test_harness_all_pass_exit_0(tmp_path):
    (tmp_path / "a.bat").write_text("@echo off\necho a\n", encoding="utf-8")
    (tmp_path / "b.bat").write_text("@echo off\necho b\nexit /b 0\n", encoding="utf-8")
    assert cli_main(["harness", str(tmp_path), "--min-pass", "2"]) == 0


@NEEDS_ORACLE
def test_harness_min_pass_failure_exit_1(tmp_path):
    (tmp_path / "a.bat").write_text("@echo off\necho a\n", encoding="utf-8")
    assert cli_main(["harness", str(tmp_path), "--min-pass", "5", "--quiet"]) == 1


@NEEDS_ORACLE
def test_harness_json_report_shape(tmp_path):
    (tmp_path / "a.bat").write_text("@echo off\necho a\n", encoding="utf-8")
    (tmp_path / "u.bat").write_text("choice /c yn\n", encoding="utf-8")
    rep = tmp_path / "rep.json"
    assert cli_main(["harness", str(tmp_path), "--json", str(rep), "--quiet"]) == 0
    data = json.loads(rep.read_text(encoding="utf-8"))
    assert data["total"] == 2
    assert data["profile"] == "v0.1"
    by_name = {c["file"]: c for c in data["cases"]}
    assert by_name["a.bat"]["parity_stdout"] == "pass"
    assert by_name["a.bat"]["parity_exit"] == "pass"
    assert by_name["u.bat"]["parity_stdout"] == "skip"
    assert by_name["u.bat"]["unsupported"] == ["BP001"]
    # bulky stdout stripped from the persisted report
    assert "cmd_stdout" not in by_name["a.bat"]


@NEEDS_ORACLE
def test_verify_against_pair(tmp_path):
    from bat2ps.emitter import convert
    from bat2ps.harness import run_ps1

    bat = tmp_path / "p.bat"
    bat.write_text("@echo off\necho pair-ok\n", encoding="utf-8")
    ps1 = tmp_path / "p.ps1"
    ps1.write_text(convert(bat.read_text(encoding="utf-8"), source_name=bat.name), encoding="utf-8")
    assert cli_main(["verify", str(bat), "--against", str(ps1)]) == 0
    _, _, code = run_ps1(ps1.resolve(), tmp_path)
    assert code == 0


@NEEDS_ORACLE
def test_doctor_ok():
    assert cli_main(["doctor"]) == 0


def test_subprocess_entrypoint():
    p = _run_cli("doctor")
    assert p.returncode == 0
    assert "profile: v0.1" in p.stdout
