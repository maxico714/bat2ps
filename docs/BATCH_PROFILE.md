# Batch profile v0.1 (frozen 2026-10-14)

This document defines the **only** batch subset `bat2ps` converts. Every
parity claim in this repo is scoped to this profile: a conversion is
"verified" only for scripts inside it. Anything else fails conversion
**loudly** with a stable `BPxxx` rule id (exit code 2) — never silently.

Machine-readable form: [`profiles/v0.1.yaml`](../profiles/v0.1.yaml).
Rule ids are never renumbered; new constructs only add ids.

## In profile

- Labels + `goto` / `call :label` (incl. `goto :eof`, `exit /b`).
  Call-target subroutines must be `goto`-free (BP011 otherwise).
- `if` / `if-else`: `errorlevel N` (**≥** semantics — the classic trap),
  `defined VAR`, `exist PATH`, string `==`, numeric
  `equ/neu/lss/leq/gtr/geq`, `/i`, `not`. `else` must sit on the same line
  as the closing `)` (as cmd requires).
- `for %%x in (...)` (quoted items, `*`/`?` wildcards), `for /f`
  (`tokens/delims/skip/eol/usebackq`; file, `"string"` and `'command'`
  sources), `for /l` (any sign of step).
- `echo` with **verbatim** spacing (cmd keeps `echo a &&` → `a `),
  `echo.`-style blanks, `@echo off/on`, `rem` / `::` comments.
- `set VAR=val` (verbatim trailing blanks), `set "VAR=val"`,
  `set VAR=` (clear), silent `set /a` (truncating `/`, C-like ops),
  `set [PREFIX]` display (A–Z sorted, like cmd).
- `setlocal` / `endlocal` scope stack (like cmd, `setlocal` zeroes
  ERRORLEVEL and `endlocal` preserves it).
- `cd` / `chdir` / `pushd` / `popd`, `shift`, `title`.
- `&&` / `||` / `&` chains (emitted natively, same process, live
  ERRORLEVEL); pipes and complex redirections run under `cmd /d /c`.
- `%VAR%`, `!VAR!` (expanded only when the script enables delayed
  expansion, otherwise literal — as cmd does), `%~dp0`-family, `%0`–`%9`,
  `%*`, `%ERRORLEVEL%`, `%CD%`.
- External commands (`dir/copy/move/del/type/sort/find/...`) via
  `cmd /d /c` passthrough (byte parity by construction).

## Out of profile (hard error at convert time)

| id | construct |
|---|---|
| BP001 | `choice` (interactive) |
| BP002 | `assoc` / `ftype` |
| BP003 | `wmic` |
| BP004 | `for /r` (recursive) |
| BP005 | `for /d` (directories) |
| BP006 | `start` (async launch) |
| BP008 | `set /p` (interactive prompt) |
| BP009 | `chcp` other than 65001 |
| BP010 | raw binary I/O |
| BP011 | call-target label containing `goto` |
| BP012 | unsupported `%~` / `%%~` modifier |
| BP020 | `if cmdextversion` |
| BP021 | `/?` help output |
| BP022 | `break` |
| BP023 | block-level chaining/redirection, control-flow inside chained lines |
| BP000 | malformed statement (parse error) |

## Escape hatches (not silent)

- External-heavy lines run through `cmd /d /c` inside the `.ps1`
  (honest fallback, parity-preserving).
- `convert --allow-partial` emits a fail-loud stub
  (`Write-Error 'unsupported: BPxxx'; exit 2`) instead of refusing.

## Known differences (honest limits)

- `%VAR%` inside parenthesised blocks reads the live value (delayed
  semantics); scripts relying on parse-time snapshots diverge.
- `%DATE%` / `%TIME%` / `%RANDOM%` are nondeterministic: excluded.
- `%~nx0`-style *name* derivatives need same-stem file names (the harness
  compares `x.bat` against a same-directory temp `.ps1`).
- Non-ASCII content assumes `chcp 65001` + UTF-8 on both sides.
- `setlocal` zeroes the *numeric* ERRORLEVEL; `%ERRORLEVEL%` right after
  `setlocal` expands empty under cmd (quirk) but reads 0 here.
- Division by zero in `set /a` errors loudly on both sides with
  different codes (no parity claimed).
