"""Constrained batch profile v0.1: rule-ids and support table."""

from __future__ import annotations

PROFILE_VERSION = "v0.1"

# Stable rule-ids for out-of-profile constructs. These ids appear in convert
# errors, emitted .ps1 markers and the honesty table. Never renumber; only add.
RULES: dict[str, str] = {
    "BP000": "malformed statement (parse error)",
    "BP001": "choice (interactive; out of profile)",
    "BP002": "assoc/ftype (out of profile)",
    "BP003": "wmic (out of profile)",
    "BP004": "for /r (recursive; out of profile v0.1)",
    "BP005": "for /d (directories; out of profile v0.1)",
    "BP006": "start (async launch; out of profile)",
    "BP007": "reserved",
    "BP008": "set /p (interactive prompt; out of profile)",
    "BP009": "chcp other than 65001 (out of profile)",
    "BP010": "raw binary I/O (out of profile)",
    "BP011": "call-target label containing goto (out of profile v0.1)",
    "BP012": "unsupported %~ / %%~ modifier (out of profile v0.1)",
    "BP020": "if cmdextversion (out of profile)",
    "BP021": "/? help output (out of profile)",
    "BP022": "break (out of profile)",
    "BP023": "block-level chaining/redirection or control-flow inside chained lines (out of profile v0.1)",
}

IN_PROFILE = [
    "labels + goto / call :label (incl. goto :eof, exit /b)",
    "if / if-else: errorlevel, defined, exist, string ==, numeric equ/neu/lss/leq/gtr/geq, /i, not",
    "for %%x in (...) do; for /f (tokens/delims/skip/eol/usebackq); for /l",
    "echo (message/blank/off/on), rem / :: comments",
    'set VAR=val, set "VAR=val", set VAR= (clear), set /a, set display',
    "setlocal / endlocal (incl. enabledelayedexpansion)",
    "cd/chdir/pushd/popd, shift, title",
    "pipes, redirection, && / || / & chaining (via cmd /c fallback)",
    "%VAR%, !VAR!, %~dp0-family, %0..%9, %*, %ERRORLEVEL%, %CD%",
    "external commands (dir/copy/move/del/type/...) via cmd /c fallback",
]

OUT_OF_PROFILE = [f"{k}: {v}" for k, v in RULES.items() if "reserved" not in v and k != "BP000"]


def describe() -> str:
    lines = [f"# Batch profile {PROFILE_VERSION} (frozen summary)", "", "## In profile"]
    lines += [f"- {item}" for item in IN_PROFILE]
    lines += ["", "## Out of profile (hard error BPxxx at convert time)"]
    lines += [f"- {item}" for item in OUT_OF_PROFILE]
    return "\n".join(lines) + "\n"
