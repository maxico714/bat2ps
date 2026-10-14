"""Emitter golden tests: batch snippet -> PowerShell snippet properties."""

import pytest

from bat2ps.emitter import (
    convert,
    parse_tokens_spec,
    ps_str,
    split_inset,
    translate_text,
)
from bat2ps.errors import ProfileError


def test_ps_str_escapes():
    assert ps_str("a'b") == "'a''b'"


def test_translate_plain_literal():
    assert translate_text("hello", {}) == "'hello'"


def test_translate_env():
    assert translate_text("hi %NAME%!", {}) == "('hi ' + $env:NAME + '!')"


def test_translate_errorlevel():
    assert translate_text("%ERRORLEVEL%", {}) == "$LASTEXITCODE"


def test_translate_arg1():
    out = translate_text("%1", {})
    assert "__bat_args[0]" in out


def test_translate_star():
    assert "-join" in translate_text("%*", {})


def test_translate_dp0():
    assert "PSCommandPath" in translate_text("%~dp0", {})


def test_translate_loop_var():
    assert translate_text("%%x", {"x": "$LX"}) == "$LX"


def test_translate_loop_mod_nx():
    out = translate_text("%%~nxi", {"i": "$LI"})
    assert "Split-Path -Leaf" in out


def test_translate_percent_escape():
    assert translate_text("100%%", {}) == "'100%'"


def test_translate_delayed():
    assert translate_text("!V!", {}) == "$env:V"


def test_split_inset_commas():
    assert split_inset("a,b;c d") == ["a", "b", "c", "d"]


def test_split_inset_quotes():
    assert split_inset('"a b" c') == ['"a b"', "c"]


def test_tokens_range():
    assert parse_tokens_spec("1-3") == [1, 2, 3]


def test_tokens_star():
    assert parse_tokens_spec("1,2,*") == [1, 2, "*"]


def test_echo_emits_write_output():
    ps = convert("echo hello\n")
    assert "Write-Output 'hello'" in ps


def test_echo_blank():
    ps = convert("echo.\n")
    assert "Write-Output ''" in ps


def test_echo_off_no_output():
    ps = convert("@echo off\n")
    assert "Write-Output" not in ps


def test_set_assign():
    ps = convert("set FOO=bar\n")
    assert "$env:FOO = 'bar'" in ps


def test_set_clear_removes():
    ps = convert("set FOO=\n")
    assert "Remove-Item env:FOO" in ps


def test_set_arith_silent_assigns():
    # Verified on cmd: `set /a` prints nothing in batch files.
    ps = convert("set /a N=1+2\n")
    assert "$env:N" in ps
    assert "Write-Output" not in ps


def test_if_errorlevel_ge():
    ps = convert("if errorlevel 1 echo bad\n")
    assert "$LASTEXITCODE -ge 1" in ps


def test_if_streq_case_sensitive():
    ps = convert('if "%A%"=="b" echo x\n')
    assert "-ceq" in ps


def test_if_i_case_insensitive():
    ps = convert('if /i "%A%"=="b" echo x\n')
    assert "-eq" in ps and "-ceq" not in ps


def test_if_defined():
    ps = convert("if defined FOO echo y\n")
    assert "Test-Path 'env:FOO'" in ps


def test_goto_state_machine():
    ps = convert("goto skip\necho no\n:skip\necho yes\n")
    assert "__bat_next" in ps and "while ($true)" in ps


def test_call_label_function():
    ps = convert("call :w\nexit /b 0\n:w\necho in-sub\n")
    assert "function __bat_sub_W" in ps


def test_exit_b_top_level():
    ps = convert("exit /b 3\n")
    assert "exit" in ps and "3" in ps


def test_external_passthrough():
    ps = convert("dir C:\\\n")
    assert "cmd /d /c" in ps


def test_chain_native_and():
    ps = convert("echo a && echo b\n")
    # Verbatim echo keeps the blank before &&.
    assert "Write-Output 'a '" in ps and "$LASTEXITCODE -eq 0" in ps


def test_chain_native_or():
    ps = convert("dir __zz >nul 2>&1 || echo fb\n")
    assert "$LASTEXITCODE -ne 0" in ps


def test_redirect_out_file():
    ps = convert("echo hi > __o.tmp\n")
    assert "Out-File" in ps and "__o.tmp" in ps


def test_redirect_nul():
    ps = convert("echo hi >nul\n")
    assert "Out-Null" in ps


def test_unsupported_raises_bp():
    with pytest.raises(ProfileError) as e:
        convert("choice /c yn\n")
    assert e.value.rule_id == "BP001"


def test_call_target_with_goto_rejected():
    with pytest.raises(ProfileError) as e:
        convert("call :s\nexit /b 0\n:s\ngoto elsewhere\n:elsewhere\necho x\n")
    assert e.value.rule_id == "BP011"


def test_call_target_eof_allowed():
    ps = convert("call :s\nexit /b 0\n:s\necho in-sub\ngoto :eof\n")
    assert "function __bat_sub_S" in ps


def test_for_l_while_loop():
    ps = convert("for /l %%i in (1,1,3) do echo %%i\n")
    assert "while" in ps and "$__l_step" in ps


def test_for_f_capture_cmd():
    ps = convert("for /f %%a in ('echo hi') do echo %%a\n")
    assert "cmd /d /c" in ps and "$__f_lines" in ps


def test_header_sets_utf8():
    ps = convert("echo x\n")
    assert "OutputEncoding" in ps and "UTF8" in ps


def test_last_line_exit():
    ps = convert("echo x\n")
    assert ps.rstrip().endswith("exit $LASTEXITCODE")
