# BUILD CHECKLIST — bat2ps

Status: SCAFFOLD. Work top-to-bottom; each gate must show REAL command output before proceeding. Circuit breaker: 3 failed attempts on one gate → stop, re-research, log in STATE.md.

## Gate 0 — Spike (riskiest assumption FIRST)

- [ ] Collect 20-script mini-corpus (npocmaka MIT files, license-tick each).
- [ ] Harness stub: run each under `cmd.exe /c` and a *hand-written* .ps1 twin for 3 scripts; normalize + diff.
- [ ] **Expected:** deterministic pass/fail per script; document any env nondeterminism found.
- [ ] Record wall times vs performance budget.
- [ ] If normalization is impossible for >30% of the 20 → STOP, re-scope profile, log ADR.

## Gate 1 — L0 static (every commit)

- [ ] `ruff check .` + `ruff format --check .` clean.
- [ ] `mypy src/` clean (strict on parser/emitter).
- [ ] `python -m pytest --collect-only -q` green.

## Gate 2 — L1 units (parser/emitter/profile)

- [ ] Lexer golden tests (≥40 cases: quotes, carets, redirects, labels).
- [ ] Parser AST goldens for every profile rule id (one positive + one negative each).
- [ ] Profile checker: every out-of-profile construct fixture → correct BP-id error, exit 2.
- [ ] Emitter goldens: setlocal stack, delayed expansion, errorlevel ≥ semantics, for /f delims.
- [ ] **Mutation sanity:** flip `>=` to `==` in errorlevel emitter → corresponding test MUST fail; restore.

## Gate 3 — L2 differential harness (the product)

- [ ] `bat2ps harness corpus/npocmaka-subset --json report.json` → ≥30 scripts parity-pass (stdout+exit).
- [ ] Second corpus (amidaware subset ≥20) runs; failures triaged (emitter bug vs profile gap vs bad fixture).
- [ ] Harness exit codes verified: 0 all-pass, 1 any-parity-fail, 3 env error.
- [ ] Determinism: run harness twice, byte-identical report.json (modulo timestamps field scrubbed).
- [ ] **Expected numbers recorded in PROGRESS.md with exact commands.**

## Gate 4 — L3 e2e

- [ ] tests/e2e: nested if + for /f + pipe script converted, verified, committed as fixture.
- [ ] Escape-hatch demo: unmappable construct → .ps1 contains `unsupported: BPxxx` + harness reports skip-with-reason (not silent pass).

## Gate 5 — L5 adversarial

- [ ] Empty file; CRLF-only; unicode var names (in-profile ones); `exit /b 42`; unterminated quote → clean errors.
- [ ] 10k-line stress under perf budget.
- [ ] Locale trap documented: non-en-US machine → documented warn behavior (not crash).

## Gate 6 — L4 clean environment

- [ ] Fresh `git clone` into temp dir; `pip install -e .`; `pytest -q`; `bat2ps doctor` all green on a clean PowerShell profile.
- [ ] README quickstart commands copy-pasted verbatim by a second process (or Docs-verifier subagent) — every step works.

## Gate 7 — Honesty & scope audit (pre-M8)

- [ ] Zero parity-% claims outside profile docs (grep README/docs).
- [ ] No TODO/FIXME/placeholder in src/ (grep).
- [ ] V1_SCOPE_CAP respected: no .vbs/wscript/installer code paths.
- [ ] THIRD_PARTY_NOTICES lists every corpus file source + license.
- [ ] Secrets scan + `git log -p | scan for keys` clean.

## Gate 8 — Packaging (G3-gated; do NOT run without operator approval)

- [ ] `python -m build` → wheel + sdist; `twine check` clean.
- [ ] Local install from wheel in fresh venv → pytest green.
- [ ] Publish ONLY at G3 with trusted publishing (OIDC), after G2 checklist.

## Definition of done (v0.1)

Gates 0–6 green with evidence logged in `PROGRESS.md` (command + actual output). Gate 7 items 1–4 green. Gate 8 prepared but not executed.
