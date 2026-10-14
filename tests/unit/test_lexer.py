"""Lexer golden tests: quotes, carets, redirects, labels, chains, pipes."""

from bat2ps.lexer import (
    classify_line,
    find_unquoted,
    join_continuations,
    logical_lines,
    split_chain_top,
    split_pipe_top,
    strip_outer_quotes,
    tokenize,
    unescape_caret,
)


def test_label_simple():
    ll = classify_line(1, ":main")
    assert ll.is_label and ll.label_name == "main"


def test_label_with_at():
    ll = classify_line(2, "@:main arg")
    assert ll.is_label and ll.echo_suppressed


def test_double_colon_is_not_label():
    ll = classify_line(1, ":: comment")
    assert not ll.is_label


def test_blank_line():
    ll = classify_line(3, "   ")
    assert ll.stripped == "" and not ll.is_label


def test_at_prefix():
    ll = classify_line(1, "@echo off")
    assert ll.echo_suppressed and ll.stripped == "echo off"


def test_crlf_split():
    lines = logical_lines("echo a\r\necho b\r\n")
    assert [ln.stripped for ln in lines] == ["echo a", "echo b"]


def test_lf_split():
    lines = logical_lines("echo a\necho b\n")
    assert len(lines) == 2


def test_continuation_joins():
    out = join_continuations("echo hello ^\nworld\n")
    assert out[0] == (1, "echo hello world")


def test_double_caret_no_continuation():
    out = join_continuations("echo a^^\nnext\n")
    assert out[0] == (1, "echo a^^")


def test_find_unquoted_pipe():
    assert find_unquoted('echo a | find "x|y"', "|") == 7


def test_find_unquoted_caret_escaped():
    assert find_unquoted("echo a^|b | more", "|") == 10


def test_find_unquoted_none():
    assert find_unquoted('echo "a|b"', "|") == -1


def test_split_chain_and():
    segs = split_chain_top("a && b")
    assert segs == [("", "a "), ("&&", " b")]


def test_split_chain_or():
    segs = split_chain_top("a||b")
    assert [op for op, _ in segs] == ["", "||"]


def test_split_chain_single_amp():
    segs = split_chain_top("a & b & c")
    assert [op for op, _ in segs] == ["", "&", "&"]


def test_split_chain_respects_parens():
    segs = split_chain_top("if 1==1 (echo a&echo b) && echo c")
    assert [op for op, _ in segs] == ["", "&&"]


def test_split_chain_respects_quotes():
    segs = split_chain_top('echo "a&&b" && echo c')
    assert len(segs) == 2


def test_split_pipe_basic():
    assert split_pipe_top("a | b | c") == ["a ", " b ", " c"]


def test_split_pipe_double_kept():
    assert split_pipe_top("a || b") == ["a || b"]


def test_split_pipe_quoted():
    assert split_pipe_top('echo "a|b" | more') == ['echo "a|b" ', " more"]


def test_unescape_caret():
    assert unescape_caret("a^&b^^c") == "a&b^c"


def test_unescape_caret_gt():
    assert unescape_caret("echo a^>b") == "echo a>b"


def test_strip_outer_quotes():
    assert strip_outer_quotes('"hello"') == "hello"
    assert strip_outer_quotes("hello") == "hello"
    assert strip_outer_quotes('"a"b') == '"a"b'


def test_tokenize_simple():
    assert tokenize("copy a.txt b.txt") == ["copy", "a.txt", "b.txt"]


def test_tokenize_quoted_spaces():
    assert tokenize('call "my file.bat" arg1') == ["call", '"my file.bat"', "arg1"]


def test_tokenize_caret():
    assert tokenize("echo a^&b") == ["echo", "a^&b"]


def test_tokenize_tabs():
    assert tokenize("set\tVAR=1") == ["set", "VAR=1"]


def test_logical_lines_bom():
    lines = logical_lines("\ufeff@echo off\n")
    assert lines[0].stripped == "echo off"


def test_label_empty_name():
    ll = classify_line(1, ":")
    assert ll.is_label and ll.label_name == ""


def test_label_case_preserved_raw():
    ll = classify_line(1, ":MyLabel")
    assert ll.label_name == "MyLabel"


def test_redirect_not_chain():
    segs = split_chain_top("echo hi > out.txt")
    assert len(segs) == 1


def test_chain_empty_segments():
    segs = split_chain_top("a&&b||c&d")
    assert [op for op, _ in segs] == ["", "&&", "||", "&"]


def test_pipe_caret():
    assert split_pipe_top("echo a^|b") == ["echo a^|b"]


def test_find_redirect():
    assert find_unquoted("echo hi > f.txt", ">") == 8


def test_multiline_block_lines_kept():
    lines = logical_lines("if 1==1 (\n  echo a\n)\n")
    assert len(lines) == 3


def test_trailing_newline_no_phantom():
    lines = logical_lines("echo a\n")
    assert len(lines) == 1


def test_empty_file():
    lines = logical_lines("")
    assert len(lines) == 1 and lines[0].stripped == ""


def test_crlf_only_file():
    lines = logical_lines("\r\n")
    assert all(ln.stripped == "" for ln in lines)


def test_echo_dot_preserved():
    ll = classify_line(1, "echo.")
    assert ll.stripped == "echo."


def test_rem_line():
    ll = classify_line(1, "REM this is a comment")
    assert ll.stripped.startswith("REM")


def test_goto_line():
    ll = classify_line(1, "goto :eof")
    assert ll.stripped == "goto :eof"
