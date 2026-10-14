"""Gate 4 escape-hatch demo: loud failure, never silent wrong output."""

import shutil
from pathlib import Path

import pytest

from bat2ps.cli import main
from bat2ps.harness import run_ps1, verify_source

FIX = Path(__file__).parent / "fixtures" / "needs_wmic.bat"


def _have_oracle() -> bool:
    return bool(shutil.which("cmd")) and bool(
        shutil.which("powershell") or shutil.which("pwsh") or shutil.which("powershell.exe")
    )


def test_strict_convert_rejects_with_bp_id():
    rc = main(["convert", str(FIX)])
    assert rc == 2


def test_partial_stub_contains_marker(tmp_path):
    out = tmp_path / "needs_wmic.ps1"
    rc = main(["convert", str(FIX), "-o", str(out), "--allow-partial"])
    assert rc == 0
    assert "unsupported: BP003" in out.read_text(encoding="utf-8")


def test_strict_harness_skips_with_reason():
    res = verify_source(FIX)
    assert res.parity_stdout == "skip" and res.parity_exit == "skip"
    assert res.unsupported == ["BP003"]


@pytest.mark.skipif(not _have_oracle(), reason="needs powershell")
def test_partial_stub_fails_loud_at_runtime(tmp_path):
    out = tmp_path / "needs_wmic.ps1"
    assert main(["convert", str(FIX), "-o", str(out), "--allow-partial"]) == 0
    _, _, code = run_ps1(out.resolve(), tmp_path)
    assert code == 2
