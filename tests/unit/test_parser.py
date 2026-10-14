"""Parser golden tests: one positive + one negative per profile rule."""

import pytest

from bat2ps.errors import ParseError, ProfileError
from bat2ps.parser import (
    Call,
    Cd,
    Chcp,
    Echo,
    EndLocal,
    Exit,
    ForF,
    ForIn,
    ForL,
    Generic,
    Goto,
    If,
    Label,
    Rem,
    SetArith,
    SetAssign,
    SetDisplay,
    SetLocal,
    Shift,
    parse_text,
)


def stmts(text):
    return parse_text(text).statements


def first(text):
    st = stmts(text)[0]
    return st


# -- comments / labels -------------------------------------------------
def test_rem():
    assert isinstance(first("rem hello"), Rem)


def test_rem_slash_variant():
    assert isinstance(first("rem/hello"), Rem)


def test_double_colon_comment():
    assert isinstance(first(":: hello"), Rem)


def test_label_canonical_upper():
    st = first(":MyLabel")
    assert isinstance(st, Label) and st.name == "MYLABEL"


def test_label_eof_name():
    st = first(":eof")
    assert isinstance(st, Label) and st.name == "EOF"


# -- goto / call / exit ------------------------------------------------
def test_goto_label():
    st = first("goto main")
    assert isinstance(st, Goto) and st.target == "MAIN" and not st.is_eof


def test_goto_colon_eof():
    st = first("goto :eof")
    assert isinstance(st, Goto) and st.is_eof


def test_goto_dynamic():
    st = first("goto %TARGET%")
    assert isinstance(st, Goto) and st.is_dynamic


def test_goto_missing_target():
    with pytest.raises(ParseError):
        parse_text("goto")


def test_call_label():
    st = first("call :work arg1")
    assert isinstance(st, Call) and st.kind == "label" and st.target == "WORK"


def test_call_file():
    st = first("call other.bat x")
    assert isinstance(st, Call) and st.kind == "file"


def test_exit_b():
    st = first("exit /b 42")
    assert isinstance(st, Exit) and st.code == "42"


def test_exit_bare():
    st = first("exit")
    assert isinstance(st, Exit) and st.is_bare


# -- echo --------------------------------------------------------------
def test_echo_message():
    st = first("echo hello world")
    assert isinstance(st, Echo) and st.kind == "message" and st.text == "hello world"


def test_echo_verbatim_trailing_space():
    st = first("echo hi ")
    assert isinstance(st, Echo) and st.text == "hi "


def test_echo_extra_leading_kept():
    st = first("echo  hi")
    assert isinstance(st, Echo) and st.text == " hi"


def test_echo_padded_off_is_noop():
    st = first("echo  off")
    assert isinstance(st, Echo) and st.kind == "noop"


def test_echo_blanks_only_is_state():
    st = first("echo    ")
    assert isinstance(st, Echo) and st.kind == "state"


def test_echo_dot_blank():
    assert first("echo.").kind == "blank"  # type: ignore[union-attr]


def test_echo_colon_blank():
    assert first("echo:").kind == "blank"  # type: ignore[union-attr]


def test_echo_off():
    assert first("@echo off").kind == "off"  # type: ignore[union-attr]


def test_echo_on():
    assert first("echo on").kind == "on"  # type: ignore[union-attr]


def test_echofoo_is_generic():
    assert isinstance(first("echofoo bar"), Generic)


# -- set ---------------------------------------------------------------
def test_set_assign():
    st = first("set FOO=bar")
    assert isinstance(st, SetAssign) and st.name == "FOO" and st.value == "bar"


def test_set_quoted_assign():
    st = first('set "FOO=bar baz"')
    assert isinstance(st, SetAssign) and st.name == "FOO" and st.value == "bar baz"


def test_set_clear():
    st = first("set FOO=")
    assert isinstance(st, SetAssign) and st.value == ""


def test_set_display_prefix():
    st = first("set FO")
    assert isinstance(st, SetDisplay) and st.prefix == "FO"


def test_set_display_all():
    st = first("set")
    assert isinstance(st, SetDisplay) and st.prefix == ""


def test_set_arith():
    st = first("set /a N=1+2")
    assert isinstance(st, SetArith) and st.name == "N" and st.op == "="


def test_set_arith_plus_eq():
    st = first("set /a N+=3")
    assert isinstance(st, SetArith) and st.op == "+="


def test_set_prompt_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("set /p X=prompt")
    assert e.value.rule_id == "BP008"


def test_setlocal():
    st = first("setlocal enabledelayedexpansion")
    assert isinstance(st, SetLocal)


def test_endlocal():
    assert isinstance(first("endlocal"), EndLocal)


# -- if ----------------------------------------------------------------
def test_if_errorlevel():
    st = first("if errorlevel 1 echo bad")
    assert isinstance(st, If) and st.cond_kind == "errorlevel" and st.number == 1


def test_if_not_errorlevel():
    st = first("if not errorlevel 2 echo ok")
    assert isinstance(st, If) and st.negated


def test_if_defined():
    st = first("if defined FOO echo yes")
    assert isinstance(st, If) and st.cond_kind == "defined" and st.var == "FOO"


def test_if_exist():
    st = first('if exist "a.txt" echo yes')
    assert isinstance(st, If) and st.cond_kind == "exist"


def test_if_streq():
    st = first('if "%A%"=="b" echo yes')
    assert isinstance(st, If) and st.cond_kind == "streq"


def test_if_streq_case_insensitive():
    st = first('if /i "%A%"=="b" echo yes')
    assert isinstance(st, If) and st.case_insensitive


def test_if_numeric_gtr():
    st = first("if 3 gtr 2 echo yes")
    assert isinstance(st, If) and st.cond_kind == "numeric" and st.op == "gtr"


def test_if_else_block():
    sc = parse_text('if "%A%"=="1" (\n  echo one\n) else (\n  echo other\n)')
    st = sc.statements[0]
    assert isinstance(st, If) and len(st.then_body) == 1 and len(st.else_body) == 1


def test_if_nested():
    sc = parse_text('if "%A%"=="1" if "%B%"=="2" echo both')
    assert isinstance(sc.statements[0], If)


def test_if_cmdextversion_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("if cmdextversion 2 echo x")
    assert e.value.rule_id == "BP020"


def test_if_malformed():
    with pytest.raises(ParseError):
        parse_text("if frobnicate")


# -- for ---------------------------------------------------------------
def test_for_in():
    st = first("for %%x in (a b c) do echo %%x")
    assert isinstance(st, ForIn) and st.var == "x" and len(st.body) == 1


def test_for_in_block():
    sc = parse_text("for %%x in (a b) do (\n  echo %%x\n)")
    assert isinstance(sc.statements[0], ForIn)


def test_for_f_tokens():
    st = first('for /f "tokens=1,2 delims=," %%a in ("x,y") do echo %%a %%b')
    assert isinstance(st, ForF) and st.var == "a" and "tokens" in st.options


def test_for_f_command():
    st = first("for /f %%a in ('echo hi') do echo %%a")
    assert isinstance(st, ForF)


def test_for_l():
    st = first("for /l %%i in (1,1,5) do echo %%i")
    assert isinstance(st, ForL) and st.start == "1" and st.step == "1" and st.end == "5"


def test_for_r_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("for /r %%x in (*.txt) do echo %%x")
    assert e.value.rule_id == "BP004"


def test_for_d_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("for /d %%x in (*) do echo %%x")
    assert e.value.rule_id == "BP005"


def test_for_missing_do():
    with pytest.raises(ParseError):
        parse_text("for %%x in (a b) echo %%x")


# -- misc --------------------------------------------------------------
def test_cd_path():
    st = first("cd subdir")
    assert isinstance(st, Cd) and st.path == "subdir"


def test_cd_bare():
    st = first("cd")
    assert isinstance(st, Cd) and st.path is None


def test_shift():
    assert isinstance(first("shift"), Shift)


def test_chcp_ok():
    assert isinstance(first("chcp 65001"), Chcp)


def test_chcp_other_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("chcp 437")
    assert e.value.rule_id == "BP009"


def test_choice_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("choice /c yn")
    assert e.value.rule_id == "BP001"


def test_wmic_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("wmic os get caption")
    assert e.value.rule_id == "BP003"


def test_assoc_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("assoc .txt")
    assert e.value.rule_id == "BP002"


def test_chain_is_compound():
    from bat2ps.parser import Chain

    st = first("echo a && echo b")
    assert isinstance(st, Chain)
    assert [op for op, _ in st.links] == ["", "&&"]


def test_pipe_is_compound():
    from bat2ps.parser import Pipeline

    st = first("echo a | more")
    assert isinstance(st, Pipeline) and len(st.parts) == 2


def test_redirect_is_compound():
    from bat2ps.parser import Redirected

    st = first("echo hi > out.txt")
    assert isinstance(st, Redirected)
    # Core keeps the blank before '>' (cmd keeps it in echo output).
    assert st.core_text == "echo hi " and st.redirs[0].target == "out.txt"


def test_redirect_append():
    from bat2ps.parser import Redirected

    st = first("echo hi >> out.txt")
    assert isinstance(st, Redirected) and st.redirs[0].op == ">>"


def test_chain_if_link():
    from bat2ps.parser import Chain, If

    st = first("echo a && if 1==1 echo b")
    assert isinstance(st, Chain)
    assert isinstance(st.links[1][1], If)


def test_block_group():
    from bat2ps.parser import Block

    st = first("(echo a)")
    assert isinstance(st, Block) and len(st.body) == 1


def test_block_redirect_suffix():
    from bat2ps.parser import Redirected

    sc = parse_text("(echo a) > __x.tmp")
    st = sc.statements[0]
    assert isinstance(st, Redirected) and st.core_text == "(echo a) "
    assert len(st.redirs) == 1


def test_if_block_redirect_suffix():
    sc = parse_text("if 1==1 (\n  echo a\n) > __x.tmp")
    st = sc.statements[0]
    assert isinstance(st, If) and len(st.suffix) == 1


def test_else_separate_line_not_else():
    from bat2ps.parser import Generic, If

    sc = parse_text("if 1==1 (\n  echo a\n)\nelse (\n  echo b\n)")
    assert isinstance(sc.statements[0], If)
    assert not sc.statements[0].else_body
    assert isinstance(sc.statements[1], Generic)  # 'else (...)' line


def test_help_switch_rejected():
    with pytest.raises(ProfileError) as e:
        parse_text("dir /?")
    assert e.value.rule_id == "BP021"


def test_script_labels_indexed():
    sc = parse_text(":a\necho x\n:b\necho y\n")
    assert sc.labels == {"A": 0, "B": 2}
    assert not sc.has_goto
