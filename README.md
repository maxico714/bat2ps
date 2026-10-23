# bat2ps

**Batch → PowerShell transpiler with machine-proven behavioral parity.**

Windows teams own thousands of unmaintainable `.bat` scripts. Manual
rewrites take weeks and silently break edge cases (`if errorlevel` is
`>=`, `echo` keeps trailing blanks, `set /a` is silent …). `bat2ps`
converts a **constrained, published batch profile** to PowerShell **and
proves the conversion** by running both scripts and diffing stdout bytes
plus exit codes.

> Scope honesty: parity is claimed **only** inside
> [`docs/BATCH_PROFILE.md`](docs/BATCH_PROFILE.md) (frozen v0.1).
> Out-of-profile constructs fail loudly (`unsupported: BPxxx`, exit 2) —
> never silently. The differential harness is the product; the
> transpiler is one consumer.

## Install

Requires Windows with `cmd.exe` + Windows PowerShell 5.1 (or pwsh) and
Python 3.10+.

```powershell
git clone https://github.com/example/bat2ps.git
cd bat2ps
pip install -e .
bat2ps doctor
```

`bat2ps doctor` smoke-tests exit-code propagation and a transpile+run
round-trip; it exits non-zero when the oracle is broken.

## Quickstart (copy-paste)

```powershell
bat2ps convert examples/deploy.bat -o deploy.ps1
bat2ps verify examples/deploy.bat
bat2ps harness corpus/npocmaka-subset --min-pass 30
bat2ps harness corpus/community-subset --min-pass 20
```

Expected (measured 2026-10-23 on Windows PowerShell 5.1, Python 3.12):

```text
deploy.bat: stdout=pass exit=pass (cmd=0 ps=0)
harness: 42/42 passed (0 failed, 0 skipped)
harness: 22/22 passed (0 failed, 0 skipped)
```

## Usage

```powershell
bat2ps convert x.bat [-o out.ps1] [--profile v0.1] [--allow-partial]
bat2ps verify x.bat [--against out.ps1]
bat2ps harness <corpus-dir> [--json report.json] [--min-pass N] [--quiet]
bat2ps doctor
```

Exit codes: `0` ok/parity-pass · `1` parity-fail or below `--min-pass` ·
`2` unsupported construct · `3` environment error.

`--allow-partial` emits a fail-loud stub
(`Write-Error 'unsupported: BPxxx'; exit 2`) instead of refusing —
belt-and-braces for pipelines that must produce a file.

## Demo

`examples/deploy.bat` converts and verifies byte-identical:

```batch
set APP_ENV=staging
if defined APP_ENV (echo config-ok) else (echo config-missing & exit /b 1)
for /l %%i in (1,1,3) do echo step-%%i
```

```powershell
bat2ps verify examples/deploy.bat
# deploy.bat: stdout=pass exit=pass (cmd=0 ps=0)
```

## How it works

```text
[bat] → Lexer → Parser (AST) → [Profile checker] → Emitter (.ps1)
                                        ↓ unsupported
                                  hard error BPxxx
[corpus] → Harness: cmd.exe /d (chcp 65001) vs powershell -NoProfile
           → normalise CRLF→LF → diff stdout bytes + exit code
           → report.json + report.md
```

- Control flow + state (`if/for/goto/call/exit/echo/set/cd/shift`)
  emit native PowerShell 5.1; `goto` becomes a label-dispatch loop,
  `call :label` becomes functions with arg save/restore.
- External commands, pipes and complex redirections run via `cmd /d /c`
  inside the `.ps1` (byte parity by construction); `&&`/`||` chains are
  emitted natively against the live `$LASTEXITCODE`.
- Verified cmd semantics baked in: `if errorlevel N` is `-ge N`, `echo`
  preserves ERRORLEVEL and keeps blanks, `set /a` is silent with
  truncating `/`, `else` binds same-line only.

## Corpus

- `corpus/npocmaka-subset/` (42 scripts, npocmaka-style topic demos,
  hand-written for this repo, MIT).
- `corpus/community-subset/` (22 realistic ops scripts: deploy, cleanup,
  log rotation, delayed expansion, dispatch).
- `tests/e2e/fixtures/` (nested if + `for /f` + pipe journey) and
  `tests/adversarial/fixtures/` (empty/huge/unicode/malformed/
  exit-code cases incl. a 10k-line stress file).

No parity claim extends beyond these plus the frozen profile.

## Honest comparison

- **LLM web converters** reach a first draft faster on weird scripts;
  they are unverified, online and data-egressing. `bat2ps` is
  deterministic, offline and proved per script.
- **Manual rewrite** reads intent and modernises idioms; `bat2ps` does
  mechanical parity inside a profile.
- **bash2pwsh / polysh / shellmap** map bash→PS or single commands;
  none do batch *script* control flow with a parity proof.

## FAQ

- *It rejects my script with `unsupported: BP004`.* Your script is
  outside profile v0.1 (`for /r` here). Shrink to the profile or wait
  for a profile bump (minor version + migration notes).
- *Can I trust the `.ps1` on another machine?* Only under the pinned
  env (en-US, 65001, same corpus files). Re-run `bat2ps verify` there.
- *Does it phone home?* No network, no telemetry, no secrets. Ever.
- *PowerShell 7?* Emitted scripts target 5.1 syntax and run on 7+ too;
  the oracle accepts either.

## Roadmap

v0.1 walking skeleton (this) → v0.5 escape hatches + honesty table →
v1.0 encoding matrix + GitHub Action + coverage report. See
[docs/ROADMAP.md](docs/ROADMAP.md).

## Contributing, security, license

- [CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md) · [SUPPORT.md](SUPPORT.md) · [GOVERNANCE.md](GOVERNANCE.md)
- [CHANGELOG.md](CHANGELOG.md) · [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- License: MIT — see [LICENSE](LICENSE).

## Verification levels reached

| area | level | evidence |
|---|---|---|
| lexer/parser/emitter units | L1 | `pytest tests/unit` (165 tests) |
| corpus differential | L2 | `bat2ps harness` 42/42 + 22/22 |
| e2e journey + escape hatch | L3 | `pytest tests/e2e` |
| clean env | L4 | fresh-clone install + `pytest` + `doctor` |
| adversarial | L5 | `pytest tests/adversarial` (unicode, 10k-line, malformed) |
| static | L0 | `ruff check`, `ruff format --check`, `mypy` (strict) |
