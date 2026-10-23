# BUILD CHECKLIST - bat2ps

Status: BUILT v0.1.0, locally verified 2026-10-23. Gate 8 is prepared but not executed (G3 owner gate).

## Gate 0 - Spike (riskiest assumption FIRST)

- [x] Collect a mini-corpus and license-tick it: 42 `npocmaka-subset` + 22 `community-subset` fixtures, hand-written; provenance recorded in `THIRD_PARTY_NOTICES.md`.
- [x] Harness stub: `bat2ps doctor` and `bat2ps verify examples/deploy.bat` both pass.
- [x] **Expected:** deterministic pass/fail per script; harness A 42/42 and B 22/22; two runs of A produce identical JSON after removing per-case `elapsed_ms`.
- [x] Record wall times: local full suite 77.82 s; clean-clone suite 92.63 s; harness A case sum 156,935 ms; slowest case 7,640 ms; 10k-line convert test 4.13 s.
- [x] Normalization failure rate is 0% across the 64 corpus files; no profile re-scope required.

## Gate 1 - L0 static (every commit)

- [x] `ruff check src tests` - All checks passed.
- [x] `ruff format --check src tests` - 17 files already formatted.
- [x] `mypy src/` - Success: no issues found in 9 source files.
- [x] `python -m pytest --collect-only -q` - green.

## Gate 2 - L1 units (parser/emitter/profile)

- [x] Lexer golden tests (41 cases: quotes, carets, redirects, labels).
- [x] Parser AST goldens for every profile rule id (positive + negative).
- [x] Profile checker: every out-of-profile construct fixture produces the correct BP-id and exit 2.
- [x] Emitter goldens: setlocal stack, delayed expansion, errorlevel `>=` semantics, for /f delims.
- [x] **Mutation sanity:** changed the errorlevel emitter from `-ge` to `-eq`; `test_if_errorlevel_ge` failed; restored and re-green.

## Gate 3 - L2 differential harness (the product)

- [x] `bat2ps harness corpus/npocmaka-subset --min-pass 30` - 42/42 passed, exit 0.
- [x] `bat2ps harness corpus/community-subset --min-pass 20` - 22/22 passed, exit 0.
- [x] Harness exit codes: 0 all-pass; 1 below `--min-pass` (`--min-pass 43` returned 1); 3 environment error (missing corpus/file returned 3).
- [x] Determinism: two corpus-A runs produced identical reports after scrubbing `elapsed_ms`.
- [x] **Expected numbers recorded** in `.agent/PROGRESS.md` with commands and outputs.

## Gate 4 - L3 e2e

- [x] `tests/e2e`: nested if + for /f + pipe script converted, verified, and covered by the suite.
- [x] Escape-hatch demo: out-of-profile construct emits `unsupported: BPxxx` and exits 2; harness reports skip-with-reason.

## Gate 5 - L5 adversarial

- [x] Empty file, CRLF-only, unicode var names, `exit /b 42`, unterminated quote handled; `tests/adversarial` 15 passed.
- [x] 10k-line stress test passed in 4.13 s, inside the 30 s convert budget and 600 s harness budget.
- [x] Locale trap documented in `docs/parity-contract.md`; no crash on the pinned en-US/chcp 65001 host.

## Gate 6 - L4 clean environment

- [x] Fresh clone into `%TEMP%`, isolated venv, `pip install -e .`, `pytest` 196 passed, `bat2ps doctor` green.
- [x] README quickstart run in that clone: convert + verify + harness A 42/42 + harness B 22/22 all green.

## Gate 7 - Honesty & scope audit (pre-M8)

- [x] No parity percentage claims outside the frozen profile/parity documentation; README counts reconciled to 42/42 + 22/22.
- [x] No TODO/FIXME/placeholder in `src/`.
- [x] `V1_SCOPE_CAP` respected: no `.vbs`/wscript/installer code paths tracked.
- [x] `THIRD_PARTY_NOTICES.md` lists corpus provenance and dev tooling.
- [x] Secrets scan of the working tree and full `git log -p --all` history is clean; `.agent/` and `AGENTS.md` are not tracked.

## Gate 8 - Packaging (G3-gated; NOT executed)

- [ ] `python -m build` -> wheel + sdist; `twine check` clean.
- [ ] Local install from wheel in a fresh venv; pytest green.
- [ ] Publish ONLY at G3 with trusted publishing (OIDC), after G2 approval.

## Definition of done (v0.1)

Gates 0-6 are green; Gate 7 items 1-5 are green. Gate 8 remains prepared but unexecuted, as required by the owner gate.
