# ROADMAP — bat2ps

Status: SCAFFOLD. SemVer from day one; Keep a Changelog.

## v0.1 — Walking skeleton (exit criteria = L2 green)

- [ ] Lexer + parser for profile v0.1 subset; unsupported → BP-id hard error.
- [ ] Emitter for same subset; setlocal/delayed-expansion scope model.
- [ ] Parity harness (cmd vs powershell, stdout-bytes + exit, pinned env).
- [ ] Corpus: npocmaka MIT subset (≥50 scripts) + second corpus skeleton (≥20).
- [ ] pytest L1+L2; `bat2ps doctor`; CI on windows-latest.
- [ ] README quickstart (executable, covered by CI).
- [ ] docs/BATCH_PROFILE.md v0.1 frozen.

**Riskiest assumption to spike first (M5):** can the harness normalize cmd/pwsh output deterministically for ≥30 real scripts? Spike = 20-script mini-corpus + harness stub before parser work.

## v0.5 — Core value

- [ ] Escape hatches (`cmd /c`, `--%`) + auto-generated honesty table in README.
- [ ] Second corpus fully integrated (amidaware + licensed samples); no coverage claims until here.
- [ ] Profile v0.2 (for /l, choice) only if corpus demand proves it.
- [ ] Report JSON schema frozen (semver'd).

## v1.0 — Production-ready

- [ ] Encoding matrix documented (65001 pinned; locale caveats).
- [ ] GitHub Action (`bat2ps-harness-action`) wrapping the harness.
- [ ] Coverage report (profile rules × corpus files).
- [ ] L4 clean-env verification script; SBOM; signed releases (G3 gate).
- [ ] THIRD_PARTY_NOTICES complete; corpus license audit signed off.

## Post-1.0 (parked, not promised)

- PowerShell→batch reverse direction; VS Code extension; interactive diff view.

## Maintenance cadence

- Profile changes = minor version + migration notes; emitter/harness bugs = patch.
- CI matrix: windows-2022 + windows-latest; Python 3.12 (pin, expand later).
