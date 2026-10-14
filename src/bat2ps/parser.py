"""Parser: LogicalLine stream -> AST (profile v0.1)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any

from .errors import ParseError, ProfileError
from .lexer import (
    LogicalLine,
    classify_line,
    logical_lines,
    split_chain_top,
    split_pipe_top,
    tokenize,
)

PROFILE = "v0.1"


# ---------------------------------------------------------------- AST nodes
@dataclass(frozen=True)
class Blank:
    lineno: int
    raw: str


@dataclass(frozen=True)
class Rem:
    lineno: int
    raw: str
    text: str


@dataclass(frozen=True)
class Label:
    lineno: int
    raw: str
    name: str  # upper-cased canonical


@dataclass(frozen=True)
class Goto:
    lineno: int
    raw: str
    target: str  # canonical upper; ':EOF' for end-of-file
    is_eof: bool
    is_dynamic: bool = False


@dataclass(frozen=True)
class Call:
    lineno: int
    raw: str
    kind: str  # 'label' | 'file' | 'raw'
    target: str
    args: str = ""


@dataclass(frozen=True)
class Exit:
    lineno: int
    raw: str
    code: str | None  # raw expression or None
    is_bare: bool = False  # plain 'exit' without /b


@dataclass(frozen=True)
class Echo:
    lineno: int
    raw: str
    kind: str  # 'message' | 'blank' | 'off' | 'on' | 'state' | 'noop'
    text: str = ""


@dataclass(frozen=True)
class SetLocal:
    lineno: int
    raw: str
    options: str = ""


@dataclass(frozen=True)
class EndLocal:
    lineno: int
    raw: str


@dataclass(frozen=True)
class SetAssign:
    lineno: int
    raw: str
    name: str
    value: str


@dataclass(frozen=True)
class SetArith:
    lineno: int
    raw: str
    name: str
    op: str  # '=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>='
    expr: str


@dataclass(frozen=True)
class SetDisplay:
    lineno: int
    raw: str
    prefix: str  # '' means bare 'set' (all)


@dataclass(frozen=True)
class If:
    lineno: int
    raw: str
    cond_kind: str  # 'errorlevel'|'defined'|'exist'|'streq'|'numeric'
    negated: bool
    case_insensitive: bool
    left: str = ""
    right: str = ""
    number: int = 0
    var: str = ""
    path: str = ""
    op: str = ""  # for numeric: equ/neu/lss/leq/gtr/geq
    then_body: list[object] = field(default_factory=list)
    else_body: list[object] = field(default_factory=list)
    suffix: tuple[Redir, ...] = ()  # clean > / >> trailer after a block body


@dataclass(frozen=True)
class ForIn:
    lineno: int
    raw: str
    var: str  # single letter, lower
    items: str  # raw inside of in (...) (unparsed; emitter splits)
    body: list[object] = field(default_factory=list)
    suffix: tuple[Redir, ...] = ()


@dataclass(frozen=True)
class ForF:
    lineno: int
    raw: str
    var: str
    options: str
    source: str  # raw inside in (...)
    usebackq: bool = False
    body: list[object] = field(default_factory=list)
    suffix: tuple[Redir, ...] = ()


@dataclass(frozen=True)
class ForL:
    lineno: int
    raw: str
    var: str
    start: str
    step: str
    end: str
    body: list[object] = field(default_factory=list)
    suffix: tuple[Redir, ...] = ()


@dataclass(frozen=True)
class Cd:
    lineno: int
    raw: str
    path: str | None  # None = bare 'cd' (print)
    pushd: bool = False


@dataclass(frozen=True)
class Popd:
    lineno: int
    raw: str


@dataclass(frozen=True)
class Shift:
    lineno: int
    raw: str


@dataclass(frozen=True)
class Title:
    lineno: int
    raw: str


@dataclass(frozen=True)
class Redir:
    """One output redirection: fd + op + target, or a dup/complex form."""

    fd: str  # '' | '1' | '2'
    op: str  # '>' | '>>'
    target: str
    complex: bool = False  # '<', '>&', '&>', missing target, ...


@dataclass(frozen=True)
class Chain:
    """``A && B || C & D`` — links carry the operator that GATES them."""

    lineno: int
    raw: str
    links: tuple[tuple[str, object], ...]  # (op_before, stmt); first op ''


@dataclass(frozen=True)
class Pipeline:
    """``A | B`` — byte-identical streaming, always run under cmd."""

    lineno: int
    raw: str
    parts: tuple[str, ...]


@dataclass(frozen=True)
class Redirected:
    """A single core statement with ``>``/``>>`` redirections."""

    lineno: int
    raw: str
    core_text: str
    redirs: tuple[Redir, ...]


@dataclass(frozen=True)
class Block:
    """A bare parenthesised group ``( ... )`` with optional > / >> suffix."""

    lineno: int
    raw: str
    body: list[object] = field(default_factory=list)
    suffix: tuple[Redir, ...] = ()


@dataclass(frozen=True)
class CompoundRaw:
    """Legacy alias: chained/piped/redirected lines (see Chain/Pipeline).

    Kept for backwards-compatible error messages; the parser no longer
    produces it.
    """

    lineno: int
    raw: str
    text: str


@dataclass(frozen=True)
class Generic:
    """Translatable-or-passthrough single external command."""

    lineno: int
    raw: str
    text: str


@dataclass(frozen=True)
class Chcp:
    lineno: int
    raw: str
    codepage: str


@dataclass(frozen=True)
class Script:
    statements: list[object]
    labels: dict[str, int]
    has_goto: bool
    has_call_label: bool


# ------------------------------------------------------------ helpers
def _is_rem(word: str) -> bool:
    w = word.lower()
    if w == "rem":
        return True
    # rem followed directly by separator char: rem,... rem; rem/ rem. rem:
    return len(w) > 3 and w.startswith("rem") and w[3] in (",", ";", "/", ".", ":", "=", " ", "\t")


def _strip_leading_at(text: str) -> str:
    t = text.strip()
    if t.startswith("@"):
        return t[1:].lstrip()
    return t


def _has_top_operators(text: str) -> bool:
    """True if text has top-level && || & | > < outside quotes/parens."""
    # Reuse chain/pipe splitting: if more than one segment, or redirect char.
    if len(split_chain_top(text)) > 1:
        return True
    if len(split_pipe_top(text)) > 1:
        return True
    # Redirect scan: > or < outside quotes (caret-aware), not part of '=='
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote and ch in (">", "<"):
            return True
        i += 1
    return False


def split_redirects(text: str) -> tuple[str, list[Redir]]:
    """Split depth-0 ``>``/``>>``/``<`` redirections off *text*.

    Returns (core, redirs). ``<``, ``>&``/``<&`` dups, fd other than ''/1/2
    and missing targets are flagged complex (run the whole line under cmd).
    """
    redirs: list[Redir] = []
    in_q = False
    depth = 0
    i = 0
    n = len(text)
    first_op_at: int | None = None
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q:
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                i += 1
                continue
            if depth == 0 and ch in (">", "<"):
                if first_op_at is None:
                    first_op_at = i
                # fd prefix: digits directly adjacent on the left
                j = i - 1
                while j >= 0 and text[j].isdigit():
                    j -= 1
                fd = text[j + 1 : i]
                if ch == "<":
                    redirs.append(Redir(fd, "<", "", complex=True))
                    i += 1
                    continue
                # '>' or '>>'; check for dup forms '>&' / '>>>&'...
                k = i
                if text.startswith(">>", i):
                    op = ">>"
                    k = i + 2
                else:
                    op = ">"
                    k = i + 1
                rest = text[k:].lstrip()
                if rest.startswith("&"):
                    redirs.append(Redir(fd, op, rest, complex=True))
                    i = n
                    continue
                # target = next token (quote-aware)
                m = 0
                tq = False
                while m < len(rest) and (tq or (rest[m] not in (" ", "\t", ">", "<", "|", "&"))):
                    if rest[m] == "^" and m + 1 < len(rest):
                        m += 2
                        continue
                    if rest[m] == '"':
                        tq = not tq
                    m += 1
                target = rest[:m].strip()
                if not target or (fd not in ("", "1", "2")):
                    redirs.append(Redir(fd, op, target, complex=True))
                else:
                    redirs.append(Redir(fd, op, target))
                i = k + (len(text[k:]) - len(text[k:].lstrip())) + m
                continue
        i += 1
    if first_op_at is None:
        return text, []
    # NOTE: no rstrip — trailing blanks before the operator belong to the
    # core (cmd keeps them: `echo B > f` writes `B `).
    return text[:first_op_at], redirs


def is_bare_redirect(text: str) -> bool:
    """True if *text* is only redirection(s) with an empty core."""
    core, redirs = split_redirects(text.strip())
    return core.strip() == "" and len(redirs) > 0


def walk_tree(stmts: list[object]) -> Iterator[object]:
    """Yield every node in the tree (depth-first)."""
    for st in stmts:
        yield st
        if isinstance(st, If):
            yield from walk_tree(st.then_body)
            yield from walk_tree(st.else_body)
        elif isinstance(st, (ForIn, ForF, ForL)):
            yield from walk_tree(st.body)
        elif isinstance(st, Chain):
            for _, sub in st.links:
                yield from walk_tree([sub])
        elif isinstance(st, Block):
            yield from walk_tree(st.body)


def _echo_remainder(raw: str, stripped: str) -> str:
    """Remainder after ``echo`` preserving verbatim trailing spaces.

    ``stripped`` (whitespace-collapsed) drives dispatch; the message itself
    is sliced from ``raw`` so trailing blanks survive (cmd keeps them:
    ``echo a &&`` prints ``a ``).
    """
    work = raw.lstrip(" \t")
    if work.startswith("@"):
        work = work[1:].lstrip(" \t")
    if len(work) < 4:
        return ""
    return work[4:]


def _parse_echo(stripped: str, lineno: int, raw: str) -> Echo:
    # stripped starts with 'echo' (any case); remainder decides kind.
    # Verified against cmd: exactly ONE separator char (blank or . : / \) is
    # skipped and the message is otherwise VERBATIM (trailing/extra blanks
    # are kept: `echo a &&` prints `a `). An all-blank remainder prints the
    # echo state. `echo off`/`echo on` need the exact single separator;
    # padded variants (`echo  off`) are silent no-ops.
    rest = _echo_remainder(raw, stripped)
    if rest == "":
        return Echo(lineno, raw, "state")
    first = rest[0]
    if first in (".", ":", "\\"):
        # echo. echo: echo\  -> blank if nothing else, else message
        msg = rest[1:]
        if msg == "":
            return Echo(lineno, raw, "blank")
        return Echo(lineno, raw, "message", msg)
    if first == "/":
        msg = rest[1:]
        if msg == "":
            return Echo(lineno, raw, "blank")
        return Echo(lineno, raw, "message", msg)
    if first in (" ", "\t"):
        msg = rest[1:]
        if msg.lower() in ("off", "on"):
            return Echo(lineno, raw, msg.lower())
        if msg.strip(" \t") == "":
            return Echo(lineno, raw, "state")
        if msg.strip().lower() in ("off", "on"):
            return Echo(lineno, raw, "noop")
        return Echo(lineno, raw, "message", msg)
    # e.g. 'echofoo' is NOT echo; caller guards word boundary. Fallback message.
    return Echo(lineno, raw, "message", rest)


def _parse_set(stripped: str, lineno: int, raw: str) -> object:
    # Verified: unquoted values keep verbatim trailing blanks
    # (`set W=abc   ` stores `abc   `), so the value is sliced from `raw`.
    work = raw.lstrip(" \t")
    if work.startswith("@"):
        work = work[1:].lstrip(" \t")
    rest = work[3:]
    if rest.strip() == "":
        return SetDisplay(lineno, raw, "")
    rest = rest.lstrip(" \t")
    # /a arithmetic
    low = rest.lower()
    if low == "/a" or low.startswith("/a ") or low.startswith("/a\t"):
        expr = rest[2:].lstrip()
        return _parse_set_arith(expr, lineno, raw)
    if low == "/p" or low.startswith("/p ") or low.startswith("/p\t"):
        raise ProfileError(
            "BP008", "set /p prompt is interactive and out of profile", lineno, PROFILE
        )
    # Display: 'set NAME' without '=' and without quote-wrapped assignment
    # Strip a wrapping "NAME=value" quoting first.
    candidate = rest.strip()
    if candidate.startswith('"') and candidate.endswith('"') and len(candidate) >= 2:
        inner = candidate[1:-1]
        if "=" in inner:
            name, _, value = inner.partition("=")
            return SetAssign(lineno, raw, name.strip(), value)
        return SetDisplay(lineno, raw, inner.strip())
    if "=" not in candidate:
        # 'set VAR name' display (prefix match). Must be a valid name-ish token.
        parts = tokenize(candidate)
        if len(parts) == 1:
            return SetDisplay(lineno, raw, parts[0])
        # 'set a b'? malformed; treat as display of first? Raise parse error.
        raise ParseError("BP000", f"malformed set statement: {stripped!r}", lineno, PROFILE)
    # Partition the UNstripped rest so trailing blanks survive in the value.
    name, _, value = rest.partition("=")
    name = name.strip()
    # 'set VAR=' clears the variable (value empty)
    if value.strip(" \t") == "":
        return SetAssign(lineno, raw, name, "")
    return SetAssign(lineno, raw, name, value)


def _parse_set_arith(expr: str, lineno: int, raw: str) -> SetArith:
    e = expr.strip().strip('"')
    # Operators longest-first
    for op in ("<<=", ">>=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "="):
        # split on op outside quotes (arithmetic rarely quoted)
        idx = e.find(op)
        if idx > 0:
            name = e[:idx].strip()
            val = e[idx + len(op) :].strip()
            if name and all(c.isalnum() or c in ("_",) for c in name):
                return SetArith(lineno, raw, name, op, val)
    raise ParseError("BP000", f"malformed set /a expression: {expr!r}", lineno, PROFILE)


def _parse_goto(stripped: str, lineno: int, raw: str) -> Goto:
    rest = stripped[4:].strip()
    if not rest:
        raise ParseError("BP000", "goto requires a label", lineno, PROFILE)
    target = rest.split()[0]
    # Dynamic goto: goto %VAR% or goto !VAR!
    if "%" in target or "!" in target:
        return Goto(lineno, raw, target, False, is_dynamic=True)
    canon = target.lstrip(":").upper()
    if canon in ("EOF",):
        return Goto(lineno, raw, ":EOF", True)
    return Goto(lineno, raw, canon, False)


def _parse_call(stripped: str, lineno: int, raw: str) -> Call:
    rest = stripped[4:].strip()
    if not rest:
        raise ParseError("BP000", "call requires a target", lineno, PROFILE)
    parts = tokenize(rest)
    target = parts[0] if parts else rest
    args = rest[len(target) :].strip()
    if target.startswith(":"):
        return Call(lineno, raw, "label", target[1:].upper() or "EOF", args)
    low = target.lower()
    if low.endswith(".bat") or low.endswith(".cmd"):
        return Call(lineno, raw, "file", target, args)
    return Call(lineno, raw, "raw", target, args)


def _parse_exit(stripped: str, lineno: int, raw: str) -> Exit:
    rest = stripped[4:].strip()
    if rest == "":
        return Exit(lineno, raw, None, is_bare=True)
    low = rest.lower()
    if low.startswith("/b"):
        code = rest[2:].strip()
        return Exit(lineno, raw, code or "0")
    return Exit(lineno, raw, rest)


# ------------------------------------------------- if/for (multiline)
def _tokenize_if_head(head: str) -> list[str]:
    return tokenize(head)


def _parse_if_condition(head: str, lineno: int) -> tuple[dict[str, Any], str]:
    """Parse 'if ...' head (without leading 'if'). Returns (cond, remainder)."""
    toks = _tokenize_if_head(head)
    i = 0
    # NOTE: /i and not are consumed here for positioning; _parse_if recomputes
    # the flags (case_insensitive, negated) from the head.
    while i < len(toks) and toks[i].lower() in ("/i", "not"):
        i += 1
    if i >= len(toks):
        raise ParseError("BP000", "malformed if statement", lineno, PROFILE)
    word = toks[i].lower()
    if word == "errorlevel":
        if i + 1 >= len(toks):
            raise ParseError("BP000", "if errorlevel requires a number", lineno, PROFILE)
        try:
            num = int(toks[i + 1].strip('"'))
        except ValueError:
            raise ParseError("BP000", "if errorlevel requires a number", lineno, PROFILE) from None
        remainder = _remainder_after(head, toks, i + 2)
        return ({"kind": "errorlevel", "number": num}, remainder)
    if word == "defined":
        if i + 1 >= len(toks):
            raise ParseError("BP000", "if defined requires a variable", lineno, PROFILE)
        remainder = _remainder_after(head, toks, i + 2)
        return ({"kind": "defined", "var": toks[i + 1]}, remainder)
    if word == "exist":
        if i + 1 >= len(toks):
            raise ParseError("BP000", "if exist requires a path", lineno, PROFILE)
        remainder = _remainder_after(head, toks, i + 2)
        return ({"kind": "exist", "path": toks[i + 1]}, remainder)
    if word == "cmdextversion":
        raise ProfileError("BP020", "if cmdextversion is out of profile", lineno, PROFILE)
    # String or numeric compare: find '==' or numeric op in the head remainder.
    rest_head = _remainder_after(head, toks, i)
    # Numeric word operators take precedence when they appear as separate words.
    for op in (" equ ", " neq ", " lss ", " leq ", " gtr ", " geq "):
        # case-insensitive search outside quotes
        pos = _find_word_op(rest_head, op.strip())
        if pos is not None:
            left = rest_head[:pos].strip()
            right = rest_head[pos + len(op.strip()) :].strip()
            opname = op.strip()
            # right may be followed by the command; split: right is one token.
            rtoks = tokenize(right)
            if not rtoks:
                raise ParseError("BP000", "malformed if comparison", lineno, PROFILE)
            right_one = rtoks[0]
            cmd = _remainder_after(right, rtoks, 1)
            return ({"kind": "numeric", "op": opname, "left": left, "right": right_one}, cmd)
    # String '==' compare
    eqpos = _find_double_eq(rest_head)
    if eqpos is None:
        raise ParseError("BP000", f"malformed if comparison: {head!r}", lineno, PROFILE)
    left = rest_head[:eqpos].strip()
    after = rest_head[eqpos + 2 :]
    # right side is one token (possibly quoted with spaces); command follows.
    rtoks = tokenize(after)
    if not rtoks:
        raise ParseError("BP000", "malformed if comparison (missing right side)", lineno, PROFILE)
    right_one = rtoks[0]
    cmd = _remainder_after(after, rtoks, 1)
    return ({"kind": "streq", "left": left, "right": right_one}, cmd)


def _remainder_after(original: str, toks: list[str], consumed: int) -> str:
    """Return substring of *original* after the first *consumed* tokens."""
    if consumed <= 0:
        return original.strip()
    # Walk original consuming tokens (quote-aware, matching tokenize).
    idx = 0
    n = len(original)
    done = 0
    while done < consumed and idx < n:
        while idx < n and original[idx] in (" ", "\t"):
            idx += 1
        if idx >= n:
            break
        # one token
        in_q = False
        while idx < n:
            ch = original[idx]
            if ch == "^" and idx + 1 < n:
                idx += 2
                continue
            if ch == '"':
                in_q = not in_q
                idx += 1
                continue
            if not in_q and original[idx] in (" ", "\t"):
                break
            idx += 1
        done += 1
    return original[idx:].strip()


def _find_word_op(text: str, op: str) -> int | None:
    """Find ' op ' as separate word outside quotes (case-insensitive)."""
    in_q = False
    i = 0
    n = len(text)
    lop = op.lower()
    L = len(op)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q and text[i : i + L].lower() == lop:
            before = text[i - 1] if i > 0 else " "
            after = text[i + L] if i + L < n else " "
            if before in (" ", "\t") and after in (" ", "\t"):
                return i
        i += 1
    return None


def _find_double_eq(text: str) -> int | None:
    in_q = False
    i = 0
    n = len(text)
    while i < n - 1:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q and text[i] == "=" and text[i + 1] == "=":
            return i
        i += 1
    return None


# The statement-list parser works over LogicalLine with an index cursor so
# if/for can consume parenthesised blocks spanning lines.
class _Cursor:
    def __init__(self, lines: list[LogicalLine]) -> None:
        self.lines = lines
        self.pos = 0

    def peek(self) -> LogicalLine | None:
        # skip nothing; blanks are real statements (ignored later)
        if self.pos < len(self.lines):
            return self.lines[self.pos]
        return None

    def next(self) -> LogicalLine | None:
        if self.pos < len(self.lines):
            ll = self.lines[self.pos]
            self.pos += 1
            return ll
        return None


def parse_text(text: str, profile: str = PROFILE) -> Script:
    lines = logical_lines(text)
    cur = _Cursor(lines)
    stmts = _parse_list(cur, stop_at_close=False)
    labels: dict[str, int] = {}
    has_goto = False
    has_call = False
    for idx, st in enumerate(stmts):
        if isinstance(st, Label):
            labels.setdefault(st.name, idx)
    for st in walk_tree(stmts):
        if isinstance(st, Goto):
            has_goto = True
        elif isinstance(st, Call) and st.kind == "label":
            has_call = True
    _check_profile(stmts, profile)
    return Script(stmts, labels, has_goto, has_call)


def _match_paren_same_line(s: str) -> int | None:
    """Index of the ')' matching the '(' at position 0 (same string)."""
    if not s.startswith("("):
        return None
    depth = 0
    in_q = False
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q and ch == "(":
            depth += 1
        elif not in_q and ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _attach_trailer(cur: _Cursor, out: list[object], idx: int, lineno: int) -> None:
    """Attach a same-line redirect trailer (``) > file``) to If/For/Block.

    Same-line trailers come only from block consumption (they reuse the
    block-start lineno). Anything else chained/piped after a block body is
    BP023. A bare ``else`` line is left for the caller (if) or the outer
    list (which reproduces cmd's `'else' is not recognized` error).
    """
    nxt = cur.peek()
    if nxt is None or nxt.lineno != lineno:
        return
    t = nxt.stripped
    if t.lower().startswith("else"):
        return
    if is_bare_redirect(t):
        _, redirs = split_redirects(t)
        if any(r.complex for r in redirs):
            raise ProfileError(
                "BP023",
                f"complex redirection after a block body is out of profile: {t!r}",
                nxt.lineno,
                PROFILE,
            )
        cur.next()
        node = out[idx]
        if isinstance(node, (If, ForIn, ForF, ForL, Block)):
            out[idx] = replace(node, suffix=tuple(redirs))
        return
    if t.startswith("&&") or t.startswith("||") or t.startswith("&") or t.startswith("|"):
        raise ProfileError(
            "BP023",
            f"chained trailer after a block body is out of profile: {t!r}",
            nxt.lineno,
            PROFILE,
        )


def _parse_list(cur: _Cursor, stop_at_close: bool) -> list[object]:
    out: list[object] = []
    while True:
        ll = cur.peek()
        if ll is None:
            break
        s = ll.stripped
        # A lone ')' (possibly followed by 'else ...') closes a block.
        if stop_at_close and (s == ")" or s.startswith(") ")):
            break
        cur.next()
        if s == "":
            out.append(Blank(ll.lineno, ll.raw))
            continue
        if ll.is_label:
            name = (ll.label_name or "").lstrip(":").upper()
            out.append(Label(ll.lineno, ll.raw, name))
            continue
        if s.startswith("::"):
            out.append(Rem(ll.lineno, ll.raw, s[2:]))
            continue
        low = s.lower()
        first = low.split(None, 1)[0] if low.split(None, 1) else ""
        first_word = first
        if _is_rem(first_word):
            out.append(Rem(ll.lineno, ll.raw, s))
            continue
        if first_word == "if":
            if_node = _parse_if(cur, ll)
            out.append(if_node)
            _attach_trailer(cur, out, len(out) - 1, ll.lineno)
            continue
        if first_word == "for":
            for_node = _parse_for(cur, ll)
            out.append(for_node)
            _attach_trailer(cur, out, len(out) - 1, ll.lineno)
            continue
        if s.startswith("("):
            # Bare group: consume via cursor only when the whole logical line
            # is the group; anything after it goes through _parse_single
            # (pipes/chains/redirects run under cmd for byte parity).
            close = _match_paren_same_line(s)
            if close is not None and s[close + 1 :].strip() == "":
                cur.next()
                try:
                    body = _consume_paren_block(cur, s, ll.lineno, ll.raw)
                except ParseError as e:
                    raise ProfileError(
                        "BP023", f"unbalanced group: {e.message}", ll.lineno, PROFILE
                    ) from e
                out.append(Block(ll.lineno, ll.raw, body))
                _attach_trailer(cur, out, len(out) - 1, ll.lineno)
                continue
        # Single-line statements (chains/pipes/redirects structured inside
        # _parse_single).
        out.append(_parse_single(ll))
    return out


def _parse_core(text: str, lineno: int, raw: str) -> object:
    """Parse one operator-free statement core (no chains/pipes/redirects).

    Routes leading ``if``/``for``/``(...)`` through single-line mini parses;
    anything else goes through :func:`_parse_single`.
    """
    # NOTE: classify preserves the unstripped raw so echo keeps verbatim
    # trailing blanks (only dispatch uses the stripped form).
    ll = classify_line(lineno, text)
    t = ll.stripped
    if t == "":
        return Blank(lineno, raw)
    low = t.lower()
    first = low.split(None, 1)[0] if low.split(None, 1) else ""
    if first == "if":
        mini = _Cursor([classify_line(lineno, t)])
        try:
            lst = _parse_list(mini, stop_at_close=False)
        except ParseError as e:
            raise ProfileError(
                "BP023", f"multi-line if inside chained line: {e.message}", lineno, PROFILE
            ) from e
        if len(lst) != 1:
            raise ProfileError(
                "BP023", f"unexpected trailing text after if body: {t!r}", lineno, PROFILE
            )
        return lst[0]
    if first == "for":
        mini = _Cursor([classify_line(lineno, t)])
        try:
            lst = _parse_list(mini, stop_at_close=False)
        except ParseError as e:
            raise ProfileError(
                "BP023", f"multi-line for inside chained line: {e.message}", lineno, PROFILE
            ) from e
        if len(lst) != 1:
            raise ProfileError(
                "BP023", f"unexpected trailing text after for body: {t!r}", lineno, PROFILE
            )
        return lst[0]
    if t.startswith("("):
        if _match_paren_same_line(t) is None:
            raise ProfileError(
                "BP023", f"multi-line group inside chained line: {t!r}", lineno, PROFILE
            )
        mini = _Cursor([classify_line(lineno, t)])
        try:
            body = _consume_paren_block(mini, t, lineno, raw)
        except ParseError as e:
            raise ProfileError("BP023", f"bad group: {e.message}", lineno, PROFILE) from e
        # Any same-line trailer (chain/pipe/redirect) was split off before
        # _parse_core ran. _consume must not need follow-up lines here (the
        # group was verified to close on this line); anything consumed means
        # a multi-line group inside a chained line.
        if mini.pos != 0:
            raise ProfileError(
                "BP023", f"multi-line group inside chained line: {t!r}", lineno, PROFILE
            )
        return Block(lineno, raw, body)
    return _parse_single(ll)


def _parse_single(ll: LogicalLine) -> object:
    s = ll.stripped
    lineno = ll.lineno
    raw = ll.raw
    low = s.lower()
    if s == "" or s.startswith("::"):
        return Rem(lineno, raw, s) if s else Blank(lineno, raw)
    # 1. chains (&& / || / & at depth 0)
    segs = split_chain_top(s)
    if len(segs) > 1:
        links: list[tuple[str, object]] = []
        for op, seg in segs:
            if seg.strip() == "":
                # `cmd &&` / `&& cmd`: let cmd reproduce the syntax error.
                return Generic(lineno, raw, s)
            links.append((op, _parse_core(seg, lineno, raw)))
        return Chain(lineno, raw, tuple(links))
    # 2. pipes
    parts = split_pipe_top(s)
    if len(parts) > 1:
        if any(p.strip() == "" for p in parts):
            return Generic(lineno, raw, s)
        return Pipeline(lineno, raw, tuple(p.strip() for p in parts))
    # 3. redirections
    core, redirs = split_redirects(s)
    if redirs:
        return Redirected(lineno, raw, core, tuple(redirs))
    first = low.split(None, 1)[0] if low.split() else ""
    if _is_rem(first):
        return Rem(lineno, raw, s)
    if first == "goto":
        return _parse_goto(s, lineno, raw)
    if first == "call":
        return _parse_call(s, lineno, raw)
    if first == "exit":
        return _parse_exit(s, lineno, raw)
    if first == "setlocal":
        return SetLocal(lineno, raw, s[8:].strip())
    if first == "endlocal":
        return EndLocal(lineno, raw)
    if first == "echo" and (
        len(s) == 4 or (len(s) > 4 and s[4] in (" ", "\t", ".", ":", "/", "\\"))
    ):
        return _parse_echo(s, lineno, raw)
    if low.startswith(("echo.", "echo:", "echo/", "echo\\")):
        return _parse_echo(s, lineno, raw)
    if first == "set" and (len(s) == 3 or (len(s) > 3 and s[3] in (" ", "\t", "/", '"'))):
        return _parse_set(s, lineno, raw)
    if first in ("cd", "chdir"):
        rest = s[len(first) :].strip()
        if rest == "" or rest == "/?":
            if rest == "/?":
                raise ProfileError("BP021", "help switches are out of profile", lineno, PROFILE)
            return Cd(lineno, raw, None)
        # 'cd /d path' — keep /d, emitter handles.
        return Cd(lineno, raw, rest)
    if first == "pushd":
        return Cd(lineno, raw, s[5:].strip() or None, pushd=True)
    if first == "popd":
        return Popd(lineno, raw)
    if first == "shift":
        return Shift(lineno, raw)
    if first == "title":
        return Title(lineno, raw)
    if first == "chcp":
        rest = s[4:].strip()
        parts = rest.split()
        cp = parts[0] if parts else ""
        return Chcp(lineno, raw, cp)
    if first == "choice":
        raise ProfileError("BP001", "'choice' is interactive and out of profile", lineno, PROFILE)
    if first in ("assoc", "ftype"):
        raise ProfileError("BP002", f"'{first}' is out of profile", lineno, PROFILE)
    if first == "wmic":
        raise ProfileError("BP003", "'wmic' is out of profile", lineno, PROFILE)
    # Help switches are documentation, not convertible behaviour.
    for tok in tokenize(s):
        if tok == "/?":
            raise ProfileError("BP021", "'/?' help output is out of profile", lineno, PROFILE)
    return Generic(lineno, raw, s)


def _parse_block_or_single(cur: _Cursor, text: str, lineno: int, raw: str) -> list[object]:
    """Parse an if/for body given as remainder text + following lines."""
    t = text.strip()
    if t.startswith("("):
        return _consume_paren_block(cur, t, lineno, raw)
    if t == "":
        return []
    # single command on the same line
    sub = classify_line(lineno, t)
    if t.lower().startswith("if "):
        # nested if on one line: parse recursively via mini-cursor
        mini = _Cursor([sub])
        return _parse_list(mini, stop_at_close=False)
    if t.lower().startswith("for "):
        mini = _Cursor([sub])
        return _parse_list(mini, stop_at_close=False)
    return [_parse_single(sub)]


def _consume_paren_block(cur: _Cursor, first_remainder: str, lineno: int, raw: str) -> list[object]:
    """Consume lines through the matching ')' of the block opening in
    *first_remainder* (which starts with '('), then parse the inner lines."""
    # Gather subsequent raw lines until parens balance to zero.
    depth = 0
    in_q = False
    inner_chunks: list[str] = []
    # Process first remainder after '('
    rest = first_remainder[1:]  # after '('
    # We scan rest + following lines char-wise; when depth returns to 0 the
    # block ends and anything after ')' on that line is the trailer.
    trailer = ""
    lines_consumed_extra = 0

    def scan_chunk(chunk: str) -> tuple[str, bool, str]:
        nonlocal depth, in_q
        j = 0
        inner: list[str] = []
        while j < len(chunk):
            ch = chunk[j]
            if ch == "^" and j + 1 < len(chunk):
                inner.append(ch)
                inner.append(chunk[j + 1])
                j += 2
                continue
            if ch == '"':
                in_q = not in_q
                inner.append(ch)
                j += 1
                continue
            if not in_q and ch == "(":
                depth += 1
                inner.append(ch)
                j += 1
                continue
            if not in_q and ch == ")":
                if depth == 0:
                    # In _consume, depth counts the opening '(' as 1.
                    pass
                depth -= 1
                if depth == 0:
                    # block ends here
                    return ("".join(inner), True, chunk[j + 1 :])
                inner.append(ch)
                j += 1
                continue
            inner.append(ch)
            j += 1
        return ("".join(inner), False, "")

    depth = 1
    done = False
    piece, done, trailer = scan_chunk(rest)
    inner_chunks.append(piece)
    while not done:
        nxt = cur.next()
        if nxt is None:
            raise ParseError("BP000", "unbalanced parenthesis", lineno, PROFILE)
        lines_consumed_extra += 1
        # A label inside a block is legal batch; keep the raw text (parser
        # will classify it when we re-parse the inner text).
        piece, done, trailer = scan_chunk(nxt.stripped)
        inner_chunks.append(piece)
    inner_text = "\n".join(inner_chunks)
    inner_lines = logical_lines(inner_text if inner_text else "")
    mini = _Cursor(inner_lines)
    body = [s for s in _parse_list(mini, stop_at_close=False) if not isinstance(s, Blank)]
    # Stash trailer for the caller via cursor pushback trick: if trailer has
    # content (e.g. 'else (...)'), insert it as the next line to parse.
    if trailer.strip():
        ll = classify_line(lineno, trailer.strip())
        cur.lines.insert(cur.pos, ll)
    return body


def _parse_if(cur: _Cursor, ll: LogicalLine) -> If:
    head = ll.stripped[2:].strip()  # after 'if'
    # /i and not flags (any order) precede the condition.
    ci = False
    neg = False
    toks = tokenize(head)
    i = 0
    while i < len(toks) and toks[i].lower() in ("/i", "not"):
        if toks[i].lower() == "/i":
            ci = True
        else:
            neg = not neg
        i += 1
    cond, remainder = _parse_if_condition(head, ll.lineno)
    then_body = _parse_block_or_single(cur, remainder, ll.lineno, ll.raw)
    else_body: list[object] = []
    # cmd only accepts `else` on the SAME logical line as the then-body's
    # closing ')'. A separate-line `else` is executed as a (failing) command.
    # Same-line elses arrive via block-consumption trailers reusing ll.lineno.
    nxt = cur.peek()
    if nxt is not None and nxt.lineno == ll.lineno and nxt.stripped.lower().startswith("else"):
        cur.next()
        erest = nxt.stripped[4:].strip()
        else_body = _parse_block_or_single(cur, erest, nxt.lineno, nxt.raw)
    kind = str(cond.get("kind"))
    return If(
        lineno=ll.lineno,
        raw=ll.raw,
        cond_kind=kind,
        negated=neg,
        case_insensitive=ci,
        left=str(cond.get("left", "")),
        right=str(cond.get("right", "")),
        number=int(cond.get("number", 0)),
        var=str(cond.get("var", "")),
        path=str(cond.get("path", "")),
        op=str(cond.get("op", "")),
        then_body=then_body,
        else_body=else_body,
    )


# NOTE: _parse_if_condition drops the /i and not flags (positioning only);
# _parse_if recomputes them from the head text (see above).
def _parse_for(cur: _Cursor, ll: LogicalLine) -> object:
    s = ll.stripped
    lineno = ll.lineno
    rest = s[3:].strip()
    low = rest.lower()
    if low.startswith("/d"):
        raise ProfileError("BP005", "'for /d' is out of profile", lineno, PROFILE)
    if low.startswith("/r"):
        raise ProfileError("BP004", "'for /r' is out of profile", lineno, PROFILE)
    if low.startswith("/f"):
        return _parse_for_f(cur, ll, rest[2:].strip())
    if low.startswith("/l"):
        return _parse_for_l(cur, ll, rest[2:].strip())
    return _parse_for_in(cur, ll, rest)


def _split_for_in_do(text: str, lineno: int) -> tuple[str, str, str]:
    """Split '<vars> in (...) do <body>' at depth 0. Returns (vars, set, body)."""
    # find ' in ' and ' do ' as separate words outside quotes/parens
    in_pos = _find_word_outside(text, "in")
    if in_pos is None:
        raise ParseError("BP000", "for is missing 'in'", lineno, PROFILE)
    varpart = text[:in_pos].strip()
    after_in = text[in_pos + 2 :].strip()
    if not after_in.startswith("("):
        raise ParseError("BP000", "for in-set must be parenthesised", lineno, PROFILE)
    # match parens
    depth = 0
    in_q = False
    i = 0
    close = -1
    while i < len(after_in):
        ch = after_in[i]
        if ch == "^" and i + 1 < len(after_in):
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q and ch == "(":
            depth += 1
        elif not in_q and ch == ")":
            depth -= 1
            if depth == 0:
                close = i
                break
        i += 1
    if close == -1:
        # multiline set: the body parser handles continuation lines. For the
        # single-line splitter this means the closing paren is on a later line.
        # Signal to the caller by raising a dedicated error the caller catches.
        raise _MultilineSet
    itemset = after_in[1:close]
    after = after_in[close + 1 :].strip()
    # Beatles... I mean, 'do' must follow.
    if not after.lower().startswith("do"):
        raise ParseError("BP000", "for is missing 'do'", lineno, PROFILE)
    body = after[2:].strip()
    return (varpart, itemset, body)


class _MultilineSet(Exception):
    pass


def _find_word_outside(text: str, word: str) -> int | None:
    in_q = False
    depth = 0
    i = 0
    n = len(text)
    L = len(word)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            i += 2
            continue
        if ch == '"':
            in_q = not in_q
            i += 1
            continue
        if not in_q and ch == "(":
            depth += 1
            i += 1
            continue
        if not in_q and ch == ")":
            depth = max(0, depth - 1)
            i += 1
            continue
        if not in_q and depth == 0 and text[i : i + L].lower() == word.lower():
            before = text[i - 1] if i > 0 else " "
            after = text[i + L] if i + L < n else " "
            if before in (" ", "\t") and after in (" ", "\t", "("):
                return i
        i += 1
    return None


def _loop_var(token: str, lineno: int) -> str:
    t = token.strip().strip(",")
    if t.startswith("%%"):
        letter = t[2:]
    elif t.startswith("%"):
        letter = t[1:]
    else:
        raise ParseError("BP000", f"for requires a % loop variable, got {token!r}", lineno, PROFILE)
    if len(letter) != 1 or not letter.isalpha():
        raise ParseError("BP000", f"bad loop variable {token!r}", lineno, PROFILE)
    return letter.lower()


def _parse_for_in(cur: _Cursor, ll: LogicalLine, rest: str) -> ForIn:
    try:
        varpart, itemset, body = _split_for_in_do(rest, ll.lineno)
    except _MultilineSet:
        # Collect following lines until the in-set closes, then re-split.
        buf = rest
        while True:
            nxt = cur.next()
            if nxt is None:
                raise ParseError("BP000", "unbalanced for in-set", ll.lineno, PROFILE) from None
            buf += "\n" + nxt.stripped
            try:
                varpart, itemset, body = _split_for_in_do(buf, ll.lineno)
                break
            except _MultilineSet:
                continue
    var = _loop_var(varpart.split()[0], ll.lineno)
    body_stmts = _parse_block_or_single(cur, body, ll.lineno, ll.raw)
    return ForIn(ll.lineno, ll.raw, var, itemset, body_stmts)


def _parse_for_f(cur: _Cursor, ll: LogicalLine, rest: str) -> ForF:
    # rest starts after '/f'. Optional "options" quoted string, then loop var.
    r = rest.strip()
    options = ""
    usebackq = False
    if r.startswith('"'):
        # find closing quote
        end = r.find('"', 1)
        if end == -1:
            raise ParseError("BP000", "malformed for /f options", ll.lineno, PROFILE)
        options = r[1:end]
        r = r[end + 1 :].strip()
    if "usebackq" in options.lower():
        usebackq = True
    try:
        varpart, source, body = _split_for_in_do(r, ll.lineno)
    except _MultilineSet:
        buf = r
        while True:
            nxt = cur.next()
            if nxt is None:
                raise ParseError("BP000", "unbalanced for in-set", ll.lineno, PROFILE) from None
            buf += "\n" + nxt.stripped
            try:
                varpart, source, body = _split_for_in_do(buf, ll.lineno)
                break
            except _MultilineSet:
                continue
    var = _loop_var(varpart.split()[0], ll.lineno)
    body_stmts = _parse_block_or_single(cur, body, ll.lineno, ll.raw)
    return ForF(ll.lineno, ll.raw, var, options, source, usebackq, body_stmts)


def _parse_for_l(cur: _Cursor, ll: LogicalLine, rest: str) -> ForL:
    try:
        varpart, triples, body = _split_for_in_do(rest, ll.lineno)
    except _MultilineSet:
        buf = rest
        while True:
            nxt = cur.next()
            if nxt is None:
                raise ParseError("BP000", "unbalanced for in-set", ll.lineno, PROFILE) from None
            buf += "\n" + nxt.stripped
            try:
                varpart, triples, body = _split_for_in_do(buf, ll.lineno)
                break
            except _MultilineSet:
                continue
    var = _loop_var(varpart.split()[0], ll.lineno)
    parts = [p.strip() for p in triples.split(",")]
    if len(parts) != 3:
        raise ParseError("BP000", "for /l requires (start,step,end)", ll.lineno, PROFILE)
    body_stmts = _parse_block_or_single(cur, body, ll.lineno, ll.raw)
    return ForL(ll.lineno, ll.raw, var, parts[0], parts[1], parts[2], body_stmts)


def _check_profile(stmts: list[object], profile: str) -> None:
    for st in stmts:
        _check_node(st, profile)


def _check_node(node: object, profile: str) -> None:
    if isinstance(node, (If,)):
        for b in (node.then_body, node.else_body):
            for sub in b:
                _check_node(sub, profile)
    elif isinstance(node, (ForIn, ForF, ForL)):
        for sub in node.body:
            _check_node(sub, profile)
    elif isinstance(node, Chain):
        for _, sub in node.links:
            _check_node(sub, profile)
    elif isinstance(node, Block):
        for sub in node.body:
            _check_node(sub, profile)
    elif isinstance(node, Redirected):
        _check_node(_parse_core(node.core_text, node.lineno, node.raw), profile)
    elif isinstance(node, Pipeline):
        if re.search(r"(?i)(?<![A-Za-z0-9_])choice(?![A-Za-z0-9_])", node.raw):
            raise ProfileError("BP001", "'choice' is out of profile", node.lineno, profile)
    elif isinstance(node, Chcp):
        cp = node.codepage.strip()
        if cp not in ("65001", ""):
            raise ProfileError(
                "BP009", f"codepage {cp!r} is out of profile (only 65001)", node.lineno, profile
            )
    elif isinstance(node, Generic):
        low = node.text.strip().lower()
        first = low.split(None, 1)[0] if low.split() else ""
        if first == "start":
            raise ProfileError("BP006", "'start' is out of profile", node.lineno, profile)
        if first == "break":
            raise ProfileError("BP022", "'break' is out of profile", node.lineno, profile)
        if first == "choice":
            raise ProfileError("BP001", "'choice' is out of profile", node.lineno, profile)
