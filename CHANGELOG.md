# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning
follows [SemVer](https://semver.org/).

## [0.1.0] — 2026-10-14

### Added

- Constrained batch profile v0.1 (`profiles/v0.1.yaml`,
  `docs/BATCH_PROFILE.md`) with stable BPxxx rule ids.
- Lexer/parser/emitter for the profile: labels/goto, if/else, for
  (in/f/l), echo/set/setlocal/cd/shift, var expansions, chains, pipes,
  redirections; external commands via `cmd /d /c`.
- Differential parity harness (`bat2ps harness`) with JSON + Markdown
  reports; `convert`, `verify`, `doctor` CLI (exit codes 0/1/2/3).
- Corpus: 41 npocmaka-style + 22 community-style fixtures, all
  parity-passing; e2e journey; adversarial suite (unicode, 10k-line,
  malformed, exit codes); `--allow-partial` fail-loud stubs.
- Docs: README quickstart, parity contract, product/technical/roadmap/
  evidence notes; packaging (CI, CoC, security, changelog, notices).

### Verified

- `pytest` 196 tests green; harness 41/41 + 22/22; `ruff check`,
  `ruff format --check`, `mypy --strict` clean; `bat2ps doctor` green;
  mutation probe (`-ge` → `-eq`) killed at L1 and L2.
