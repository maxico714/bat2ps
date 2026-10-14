# PRODUCT — bat2ps

Status: SCAFFOLD (not built). Date: 2026-10-12.

## Problem

Legacy `.bat`/`.cmd` scripts are unmaintainable on modern Windows: no syntax highlighting worth using, no modules, no test harness, encodings fight you, and `goto` spaghetti dominates. Teams must move to PowerShell (org policy, pwsh-only runners, security review) but conversion is manual. Blog guides exist; tools don't. Every converter found is either regex-level (breaks on control flow) or an LLM web service (unverifiable, data-egress, paid credits).

## Target users (personas)

1. **Windows ops engineer (primary):** owns 50–500 .bat files from the 2000s–2010s (deploy scripts, installer wrappers, scheduled tasks). Must deliver "converted and verified" to a security reviewer. Job: convert without breaking production behavior.
2. **Build/release engineer (secondary):** CI images moving to Server Core / pwsh-only; batch steps fail. Job: get a working .ps1 fast, with proof.
3. **Consultant/migrator (tertiary):** paid per migration; parity harness = their acceptance test.

## Jobs-to-be-done

- "Convert this .bat to .ps1 and show me it behaves identically."
- "Tell me which constructs your converter doesn't support BEFORE I trust it."
- "Run the proof harness in CI so future edits don't regress."

## Value proposition (one sentence)

The only open-source batch→PowerShell converter that **proves** behavioral parity by differential execution — the harness is the product.

## Non-goals (explicit)

- Not a general batch interpreter or emulator.
- Not a .vbs/wscript/NSIS/Inno converter.
- Not 100% batch compatibility (a published profile defines the supported subset).
- Not an LLM wrapper (deterministic, offline).
- Not a PowerShell-to-batch reverse tool.

## MVP scope (MoSCoW)

**Must (v0.1 walking skeleton):**
- Parse constrained profile: labels/goto, if/else, for /f (token delims), common built-ins (echo, set, cd, dir, copy, move, del, exit, call, setlocal/endlocal, shift), %var%, %~ modifiers (subset), pipes, redirection, errorlevel checks.
- Emit .ps1; run corpus under cmd vs ps1 under pwsh; diff stdout-bytes + exit-code; JSON + human report.
- Fixture corpus committed (npocmaka subset + second corpus); pytest suite; `--doctor` self-check.

**Should (v0.5):**
- Escape hatches (`cmd /c` passthrough, `--%`) for unmappable constructs; honesty table auto-generated from test results.
- Second corpus integrated; profile document (docs/BATCH_PROFILE.md) frozen.
- CLI UX: `bat2ps convert x.bat`, `bat2ps verify x.bat`, `bat2ps harness corpus/`.

**Could (v1.0):**
- Encoding matrix (chcp 65001 pinned; documented locale limits).
- GitHub Action wrapper for the harness.
- Coverage report (which profile rules each corpus file exercises).

**Won't (this run):** .vbs, wscript, MSI/script custom actions, PowerShell→batch.

## Success criteria (measurable)

| Criterion | Measure | Command/proof |
|---|---|---|
| L1 units | Profile parser + emitter unit tests green | `pytest -q` |
| L2 integration | ≥30 corpus scripts pass differential harness (stdout+exit) | `bat2ps harness --min-pass 30` |
| L3 e2e | Full convert→run→diff on a non-trivial script (nested if + for + pipe) | fixture in tests/e2e |
| L4 clean env | Fresh clone + `pip install -e .` + pytest green on Windows host | documented in README |
| L5 adversarial | Encoding, empty files, CRLF, unicode vars, `exit /b 42`, delayed-expansion `!` cases (in-profile ones pass; out-of-profile fail loudly) | tests/adversarial/ |
| Honesty | Zero parity-% claims outside published profile; unsupported constructs → explicit `unsupported:` error, never silent wrong output | code review + tests |

## Honest comparison (where others are better)

- **LLM web converters:** faster to first draft for weird scripts; we are deterministic, offline, and *verifiable* — they are not.
- **Manual rewrite:** a human can read intent and modernize idiomatically; we do mechanical parity within a profile.
- **bash2pwsh / polysh / shellmap:** cover bash→PS or command-level mappings; none do batch *script* control flow with parity proof.
- **Inedo guide / forums:** honest documentation of the vacuum — not competitors.

## Naming & license

- Working name `bat2ps` — free on PyPI and npm (verified 2026-10-11).
- License: MIT. Corpus entries need per-file license audit → THIRD_PARTY_NOTICES before any publish (G2/G3).

## Risk register (top)

| Risk | Sev | Mitigation |
|---|---|---|
| Parity collapses on goto/delayed-expansion spaghetti | High | Constrained profile; escapes; honesty table |
| LLM converters "good enough" → zero adoption | Med | Accept (D-005: adoption ≠ done); harness-as-product positioning |
| npocmaka corpus is demos not production | Med | Second corpus required before coverage claims |
| Locale/codepage breaks byte-diff | Med | Pin chcp 65001 + en-US in parity contract; document boundary |
| Scope creep to full batch reimplementation | High | V1_SCOPE_CAP enforced in BUILD_CHECKLIST gate |
