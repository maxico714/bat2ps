"""Lexer for Windows batch files (profile v0.1).

Responsibilities:
- decode-agnostic line splitting (CRLF/LF), BOM strip
- caret line-continuation join (``^`` + newline)
- per-line classification: blank, label, comment, command
- quote/caret-aware helpers for ``| & > <`` splitting

The lexer is intentionally line-oriented: batch control flow in the
constrained profile is line + parenthesis-block oriented, so the parser
consumes LogicalLine records rather than a char token stream.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogicalLine:
    lineno: int
    raw: str
    stripped: str
    echo_suppressed: bool  # leading '@'
    is_label: bool
    label_name: str = ""


def _strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def join_continuations(text: str) -> list[tuple[int, str]]:
    """Join caret-newline continuations.

    Returns list of (first_lineno, joined_text). A caret immediately before
    CRLF/LF joins the next physical line with a single space removed
    semantics: batch removes the caret+newline entirely. We remove both.
    """
    text = _strip_bom(text)
    # Normalize newlines first but remember mapping loosely via first lineno.
    phys = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[tuple[int, str]] = []
    buf = ""
    buf_start = 1
    started = False
    for idx, line in enumerate(phys, start=1):
        # Batch requires the caret to be literally the last char; trailing
        # spaces break the continuation. '^^' is an escaped caret, not one.
        if line.endswith("^") and not line.endswith("^^"):
            # Single caret continuation (^^ is escaped caret, not continuation).
            piece = line[:-1]
            if not started:
                buf_start = idx
                started = True
            buf += piece
            continue
        if not started:
            out.append((idx, line))
        else:
            buf += line
            out.append((buf_start, buf))
            buf = ""
            started = False
    if started:
        out.append((buf_start, buf))
    return out


def classify_line(lineno: int, raw: str) -> LogicalLine:
    s = raw.strip()
    suppressed = False
    body = s
    if body.startswith("@"):
        suppressed = True
        body = body[1:].lstrip()
    is_label = False
    label_name = ""
    # '::' is a comment, not a label. Single ':' at col 0 (after @) is a label.
    if body.startswith(":") and not body.startswith("::"):
        is_label = True
        label_name = body[1:].strip().split()[0] if body[1:].strip() else ""
        # Labels may carry trailing comments; keep raw for fidelity.
    return LogicalLine(
        lineno=lineno,
        raw=raw,
        stripped=body,
        echo_suppressed=suppressed,
        is_label=is_label,
        label_name=label_name,
    )


def logical_lines(text: str) -> list[LogicalLine]:
    """Split batch source into logical lines."""
    joined = join_continuations(text)
    result: list[LogicalLine] = []
    for lineno, raw in joined:
        # Drop the phantom trailing line produced by a final newline.
        result.append(classify_line(lineno, raw))
    # Remove single trailing empty line caused by final newline for cleaner AST,
    # but keep intentionally blank files as one empty line.
    while len(result) > 1 and result[-1].stripped == "" and result[-1].raw == "":
        result.pop()
    return result


def find_unquoted(text: str, chars: str) -> int:
    """Return index of first char in *chars* outside double quotes, or -1.

    Caret escapes the next character (``^&`` is literal ``&``).
    Percent expansions (``%VAR%``) do not affect quoting.
    """
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
        if not in_quote and ch in chars:
            return i
        i += 1
    return -1


def split_unquoted(text: str, delim: str) -> list[str]:
    """Split on *delim* chars occurring outside quotes (caret-aware)."""
    parts: list[str] = []
    cur: list[str] = []
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            cur.append(ch)
            cur.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
            i += 1
            continue
        if not in_quote and ch == delim:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def split_chain_top(text: str) -> list[tuple[str, str]]:
    """Split ``cmd1 && cmd2 || cmd3 & cmd4`` at paren-depth 0, quote-aware.

    Returns list of (operator_before, segment). First segment has op ``''``.
    Operators recognised: ``&&``, ``||``, ``&`` (single). Pipes are NOT split
    here; see :func:`split_pipe_top`.
    """
    segments: list[tuple[str, str]] = []
    cur: list[str] = []
    in_quote = False
    depth = 0
    op_before = ""
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            cur.append(ch)
            cur.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
            i += 1
            continue
        if not in_quote:
            if ch == "(":
                depth += 1
                cur.append(ch)
                i += 1
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                cur.append(ch)
                i += 1
                continue
            if depth == 0 and ch == "&":
                if i + 1 < n and text[i + 1] == "&":
                    segments.append((op_before, "".join(cur)))
                    cur = []
                    op_before = "&&"
                    i += 2
                    continue
                segments.append((op_before, "".join(cur)))
                cur = []
                op_before = "&"
                i += 1
                continue
            if depth == 0 and ch == "|" and i + 1 < n and text[i + 1] == "|":
                segments.append((op_before, "".join(cur)))
                cur = []
                op_before = "||"
                i += 2
                continue
        cur.append(ch)
        i += 1
    segments.append((op_before, "".join(cur)))
    return segments


def split_pipe_top(text: str) -> list[str]:
    """Split ``a | b`` on single pipes at depth 0, quote-aware (``||`` kept)."""
    parts: list[str] = []
    cur: list[str] = []
    in_quote = False
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            cur.append(ch)
            cur.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
            i += 1
            continue
        if not in_quote:
            if ch == "(":
                depth += 1
                cur.append(ch)
                i += 1
                continue
            if ch == ")":
                depth = max(0, depth - 1)
                cur.append(ch)
                i += 1
                continue
            if depth == 0 and ch == "|":
                if i + 1 < n and text[i + 1] == "|":
                    cur.append("||")
                    i += 2
                    continue
                parts.append("".join(cur))
                cur = []
                i += 1
                continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def unescape_caret(text: str) -> str:
    """Remove caret escapes for native emission (``^&`` -> ``&`` ...)."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "^" and i + 1 < n:
            out.append(text[i + 1])
            i += 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def strip_outer_quotes(text: str) -> str:
    """Strip one pair of surrounding double quotes, if present."""
    t = text.strip()
    if len(t) >= 2 and t.startswith('"') and t.endswith('"'):
        return t[1:-1]
    return t


def tokenize(text: str) -> list[str]:
    """Whitespace-split respecting double quotes and caret escapes."""
    tokens: list[str] = []
    cur: list[str] = []
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "^" and i + 1 < n:
            cur.append(ch)
            cur.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            in_quote = not in_quote
            cur.append(ch)
            i += 1
            continue
        if not in_quote and ch in (" ", "\t"):
            if cur:
                tokens.append("".join(cur))
                cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if cur:
        tokens.append("".join(cur))
    return tokens
