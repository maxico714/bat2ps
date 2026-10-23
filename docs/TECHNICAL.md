# TECHNICAL — bat2ps

Status: Built and verified v0.1.0. Date: 2026-10-23 (design 2026-10-12). Stack rationale: Python 3.12 stdlib-first (host-verified); PowerShell oracle = system pwsh/powershell.exe.

## Architecture (C4-lite)

```
[bat file] → Lexer → Parser (AST) → [Profile checker] → Emitter (PS1)
                              ↓ unsupported construct
                        hard error (unsupported: <rule-id>)
[corpus run] → Harness: spawn cmd.exe /c script.bat
                          spawn powershell.exe script.ps1
                          normalize (CRLF, chcp) → diff stdout-bytes + exit code
                          → report.json + report.md
```

Containers: single Python package `bat2ps` (CLI via argparse). No services, no DB. Harness = subprocess orchestration only.

## Constrained batch profile (v0.1 — to be frozen as docs/BATCH_PROFILE.md)

**In profile:** labels + `goto`/`call :label`; `if`/`if else` (errorlevel, string compare, exist, defined); `for /f` with token delims + simple set; `for %%x in (...)`; built-ins: echo, set, setlocal/endlocal (incl. enabledelayedexpansion), cd/chdir, dir (subset of switches), copy/move/del (basic), type, exit /b, call, shift, rem; `%VAR%` + `%~dp0 nx f` modifiers (subset); `|` pipes; `>`/`>>` redirection; `&&`/`||`; `errorlevel` checks; `%ERRORLEVEL%`.

**Out of profile (hard error at convert time):** `goto :eof` edge cases beyond documented; `for /r`, `for /l` (v0.1); `choice`; `assoc`/`ftype`; `wmic`; dynamic env expansion beyond setlocal; `.vbs` calls; `start /wait` complex; custom codepages ≠ 65001; raw binary I/O.

Every out-of-profile construct maps to a stable rule-id (`BP012`, …) surfaced in errors and the honesty table.

## Parity contract (the product core)

A conversion is "verified" iff, under the pinned environment:

1. `cmd.exe /c run.bat` and `powershell.exe -NoProfile -File run.ps1` both terminate.
2. Normalized stdout bytes are equal (normalization: CRLF→LF; OEM→UTF-8 under chcp 65001 pinned by harness).
3. Exit codes are equal (`exit /b N` / `$LASTEXITCODE`).
4. stderr compared but non-blocking (warn-level; Windows error strings are localized — documented limitation).

Pinned env (harness injects): `chcp 65001`, `cmd /d`, `powershell -NoProfile -ExecutionPolicy Bypass`, deterministic cwd, fixtures avoid timestamp/random built-ins (or scrub them).

## Emitter rules (sketch)

- `set VAR=val` → `$env:VAR = 'val'` inside a function scope with setlocal/endlocal emulation via a stack (`$BatScope`).
- `%VAR%` → `${env:VAR}` or scope lookup; delayed `!VAR!` → `$script:BatDelayed.VAR` under enabledelayedexpansion.
- `if errorlevel 1` → `if ($LASTEXITCODE -ge 1)` (semantics: ≥, verified against cmd behavior — this is a known trap).
- `for /f "tokens=1,2 delims=," %%a in ('cmd')` → pipeline over `cmd /c` capture with explicit encoding.
- Unmappable → `Write-Error 'unsupported: BPxxx' ; exit 2` (fail loud in the .ps1 too, belt-and-braces).

## Interfaces

- CLI: `bat2ps convert <file.bat> [-o out.ps1] [--profile v0.1]`; `bat2ps verify <file.bat> [--against out.ps1]`; `bat2ps harness <corpus-dir> [--json out.json] [--min-pass N]`; `bat2ps doctor`.
- Report JSON schema: `{file, profile, supported: [rule_ids], unsupported: [rule_ids], parity: {stdout: pass|fail|skip, exit: pass|fail, cmd_exit, ps_exit, first_diff_offset}}`.
- Exit codes: 0 ok/parity-pass; 1 parity-fail; 2 unsupported construct; 3 harness/environment error (doctor-friendly).

## Data model

No persistence. Fixtures = directory tree of `.bat` files + optional `.expected/` (for hand-verified edge cases where live oracle is insufficient — rare; prefer live differential).

## Threat model (STRIDE-lite)

- Corpus scripts are untrusted input to *our parser* (not executed on parse) → parser must be memory-bounded, no `eval`.
- Harness executes corpus on the host → **fixtures must be reviewed**; harness runs with cwd in a temp sandbox dir; never elevated; document that running arbitrary .bat is dangerous (users bring their own corpus at own risk; our shipped corpus is audited).
- No network, no telemetry, no secrets. `--doctor` prints tool versions only.

## Error model

All errors carry rule-id + file:line + profile version. Parser errors ≠ emitter errors ≠ parity failures (distinct exit codes). No silent coercion.

## Performance budget

- Convert 1k-line .bat < 2s.
- Harness per script: overhead < 1.5× (script_runtime × 2) + 300ms spawn floor.
- Corpus of 200 scripts: < 10 min wall on dev host.

## Testing strategy (verification ladder)

- L0: ruff + mypy + pytest collect.
- L1: lexer/parser/emitter golden tests (bat snippet → ps1 snippet); profile checker table tests.
- L2: differential harness on committed corpus (CI = Windows runner).
- L3: e2e convert+verify on 3 hand-picked complex scripts.
- L4: fresh-clone script in README executed by CI.
- L5: adversarial fixtures (empty, CRLF-only, unicode, exit codes, unterminated quotes, 10k-line stress).

## Packaging / distribution

PyPI `bat2ps` (name free, verified). GitHub Releases with wheel. Optional later: scoop manifest. Trusted publishing (OIDC) at G3 only.

## Repo layout (target)

```
bat2ps/
  src/bat2ps/{lexer.py,parser.py,profile.py,emitter.py,harness.py,cli.py,doctor.py}
  profiles/v0.1.yaml
  corpus/{npocmaka-subset,community-scripts-subset}/
  tests/{unit,integration,adversarial,e2e}/
  docs/{PRODUCT,TECHNICAL,ROADMAP,BATCH_PROFILE,parity-contract}.md
```
