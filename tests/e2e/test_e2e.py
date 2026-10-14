"""L3 end-to-end: convert -> run -> diff on a non-trivial script."""

import shutil
from pathlib import Path

import pytest

from bat2ps.emitter import convert
from bat2ps.harness import verify_source

FIX = Path(__file__).parent / "fixtures" / "complex_roster.bat"


def _have_oracle() -> bool:
    return bool(shutil.which("cmd")) and bool(
        shutil.which("powershell") or shutil.which("pwsh") or shutil.which("powershell.exe")
    )


def test_e2e_convert_runs():
    ps1 = convert(FIX.read_text(encoding="utf-8-sig"), source_name=FIX.name)
    assert "Write-Output" in ps1
    assert ps1.rstrip().endswith("exit $LASTEXITCODE")


@pytest.mark.skipif(not _have_oracle(), reason="needs cmd + powershell")
def test_e2e_parity_stdout_and_exit():
    res = verify_source(FIX)
    assert res.error == "", res.error
    assert (res.parity_stdout, res.parity_exit) == ("pass", "pass")
    assert "eng-ok" in res.cmd_stdout
    assert "pipe-used" in res.cmd_stdout
