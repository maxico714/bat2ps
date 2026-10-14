# Security policy

bat2ps is a local-first developer tool: no network, no telemetry, no
accounts, no secrets. The harness **executes** `.bat`/`.ps1` files on
your machine — only run corpora you trust, with a normal (non-elevated)
shell, as the harness does.

## Supported versions

| version | supported |
|---|---|
| 0.1.x | yes (latest patch) |
| < 0.1 | no |

## Reporting a vulnerability

- **Do not** open a public issue for security bugs.
- Email the maintainers (see `GOVERNANCE.md`) with: affected version,
  repro steps, and impact. Expect an acknowledgement within 5 business
  days and a fix or mitigation plan within 30 days.
- We will credit reporters (opt-in) in `CHANGELOG.md`.

## Scope notes

- Parser input is untrusted text (never `eval`'d); the harness runs only
  files you point it at, in the script's directory, with stdin closed.
- Dependency footprint is zero at runtime (stdlib only); CI pins
  `actions/*` to commit SHAs and runs dependency review.
