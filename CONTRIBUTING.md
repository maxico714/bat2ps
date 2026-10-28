# Contributing to bat2ps

Setup in under 5 minutes (Windows, Python 3.10+):

```powershell
git clone https://github.com/maxico714/bat2ps.git
cd bat2ps
pip install -e .
pip install pytest ruff mypy
bat2ps doctor
pytest -q
```

## Commands

```powershell
ruff check src tests
ruff format --check src tests
mypy src/
python -m pytest --collect-only -q
pytest -q
bat2ps harness corpus/npocmaka-subset --min-pass 30
bat2ps harness corpus/community-subset --min-pass 20
```

Every commit must keep `ruff`, `mypy --strict`, the full suite and both
harnesses green. Gate rules live in `BUILD_CHECKLIST.md`.

## Rules

- Smallest correct change; no unrelated edits; no `TODO`/`FIXME`/placeholders.
- New batch behaviour needs: a unit test, a corpus fixture proving parity,
  and a profile-doc line (or a BPxxx rejection + test).
- Never weaken a check to get green — fix the cause.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, …).
- PRs: describe evidence (commands + outputs), note the verification level
  (L0–L5), and call out anything unverified.

## Reporting bugs

Use the bug-report form. Include the `.bat` snippet, `bat2ps` version,
`bat2ps doctor` output, and the `verify` diff. Security issues: see
`SECURITY.md` (do not file publicly).
