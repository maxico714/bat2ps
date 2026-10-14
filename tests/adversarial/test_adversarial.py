"""L5 adversarial: empty/huge/malformed/unicode/exit-code cases."""

import shutil
import time
from pathlib import Path

import pytest

from bat2ps.emitter import convert
from bat2ps.errors import Bat2PsError
from bat2ps.harness import verify_source

FIX = Path(__file__).parent / "fixtures"


def _have_oracle() -> bool:
    return bool(shutil.which("cmd")) and bool(
        shutil.which("powershell") or shutil.which("pwsh") or shutil.which("powershell.exe")
    )


needs_oracle = pytest.mark.skipif(not _have_oracle(), reason="needs cmd + powershell")

PARITY_CASES = [
    "empty.bat",
    "crlf_only.bat",
    "blanks.bat",
    "unicode_vars.bat",
    "exit_255.bat",
    "echo_unterminated.bat",
    "caret_cont.bat",
    "delay_off_bang.bat",
    "empty_for_in.bat",
    "special_chars.bat",
    "redir_nul.bat",
    "long_line.bat",
]


@needs_oracle
@pytest.mark.parametrize("name", PARITY_CASES)
def test_adversarial_parity(name):
    res = verify_source(FIX / name)
    assert res.error == "", f"{name}: {res.error}"
    assert (res.parity_stdout, res.parity_exit) == ("pass", "pass"), name


@needs_oracle
def test_stress_10k_under_budget():
    t0 = time.monotonic()
    text = (FIX / "stress_10k.bat").read_text(encoding="utf-8-sig")
    convert(text, source_name="stress_10k.bat")
    conv_ms = int((time.monotonic() - t0) * 1000)
    assert conv_ms < 30_000, f"convert took {conv_ms}ms"
    res = verify_source(FIX / "stress_10k.bat")
    total_ms = int((time.monotonic() - t0) * 1000)
    assert (res.parity_stdout, res.parity_exit) == ("pass", "pass"), res.error
    assert total_ms < 600_000, f"harness took {total_ms}ms"


def test_unterminated_if_is_clean_error():
    with pytest.raises(Bat2PsError) as e:
        convert("if 1==1 (echo oops\n")
    assert e.value.rule_id in ("BP000", "BP023")


def test_empty_converts_to_header_only():
    ps1 = convert("", source_name="empty.bat")
    assert "Write-Output" not in ps1
    assert ps1.rstrip().endswith("exit $LASTEXITCODE")
