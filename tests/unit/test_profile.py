"""Profile checker: every out-of-profile construct -> correct BP-id, exit 2."""

import subprocess
import sys

import pytest

from bat2ps.errors import ProfileError
from bat2ps.parser import parse_text
from bat2ps.profile import OUT_OF_PROFILE, RULES


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("choice /c yn", "BP001"),
        ("assoc .txt", "BP002"),
        ("ftype txtfile", "BP002"),
        ("wmic os get caption", "BP003"),
        ("for /r %%x in (*) do echo %%x", "BP004"),
        ("for /d %%x in (*) do echo %%x", "BP005"),
        ("start notepad.exe", "BP006"),
        ("set /p X=hi", "BP008"),
        ("chcp 437", "BP009"),
        ("if cmdextversion 2 echo x", "BP020"),
        ("dir /?", "BP021"),
    ],
)
def test_rule_ids(source, rule):
    with pytest.raises(ProfileError) as e:
        parse_text(source)
    assert e.value.rule_id == rule
    assert str(e.value).startswith("unsupported: " + rule)


def test_rules_documented():
    assert "BP001" in RULES and "BP009" in RULES
    assert any("choice" in line for line in OUT_OF_PROFILE)


def test_cli_exit_code_2_on_unsupported(tmp_path):
    bat = tmp_path / "x.bat"
    bat.write_text("choice /c yn\n", encoding="utf-8")
    p = subprocess.run(
        [sys.executable, "-m", "bat2ps.cli", "convert", str(bat)],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2
    assert "unsupported: BP001" in p.stderr
