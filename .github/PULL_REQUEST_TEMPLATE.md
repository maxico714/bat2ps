# Pull request

## What + evidence

- Commands run and their real output:
- Verification level (L0–L5):

## Checklist

- [ ] `ruff check`, `ruff format --check`, `mypy src/` clean
- [ ] `pytest -q` green; both harnesses meet `--min-pass`
- [ ] New behaviour has a unit test + corpus fixture + profile-doc line
      (or a BPxxx rejection + test)
- [ ] Nothing unverified is claimed as working
