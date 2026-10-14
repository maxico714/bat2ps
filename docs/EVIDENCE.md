# EVIDENCE — bat2ps (verified research summary)

Source: round-3 M2 verifier V-T + skeptic-r3 + gap-evidence-r3. Ledger row 35. ADR-003. Access dates 2026-10-11.

## Gap class: A (nothing mature found)

5+ independent sources agree no mature OSS batch→PS *script* transpiler exists:
- Inedo guide: "There are no translation tools available (trust me, we've looked), so you'll need to do it by hand, line-by-line."
- forums.powershell.org/t/21609 (2023, 13,404 views): top answer "**No.**"
- SuperUser 851610 (2014, 66,805 views): answers recommend manual + ScriptoMatic (not a converter).
- Matches checked and rejected: nyabkun/bash-to-powershell-converter 61★ (bash→PS regex only); ffgenius/polysh 0★ (7 CMD→PS commands, no control flow); shellmap/toolsti web tools ("IF/FOR/GOTO marked for manual rewrite"); hulo-lang/hulo 148★ (wrong direction: compiles TO batch).

## Demand hook: 3/5 (capped honestly)

- Real artifacts: forum 13.4k views; SuperUser 66.8k; SO 67789875 (7,045 views); nextcloud/client-building#142 (2025-04, human-port request, 0 comments).
- Cap reason: HN 43360552 sentiment = "hand-rewrite or LLM"; paid LLM converters exist (CodingFleet); demand = "help migrating", not proven "buy this artifact". Per D-006, hook stays 3.

## Host feasibility: VERIFIED

- `cmd.exe` + `powershell.exe` exit-code propagation smoke-tested on this host (2026-10-11): exit 42 propagated by both.
- Fixture corpus: npocmaka/batch.scripts = MIT, 1,135★, 197 .bat files at HEAD (tree API count). amidaware/community-scripts 173★ MIT-listed.
- Name `bat2ps` free on PyPI + npm (404 checks 2026-10-11).

## Correction ledger (claims → verified facts)

| Claim in research | Verified fact |
|---|---|
| SO "11k views" for batch→PS | not found; misattribution of SO 40145333 (PS→bash, 12,771 views) |
| SuperUser ~4k views | 66,805 views |

## Skeptic failure scenarios (skeptic-r3) → binding mitigations

1. Batch semantics hostile to general parity (delayed expansion corrupts `!`; cmd→PS quoting mismatch, SO 42601270; `if errorlevel 1` is ≥1; localized error messages break byte-diff) → **constrained profile + parity contract + en-US/chcp pin**.
2. npocmaka = topic-sorted snippets not production scripts → **second corpus before any coverage claim**.
3. Free web LLM converters own the narrative → **harness-as-product positioning; "prove your conversion"**.
4. Bimodal value (thin wrappers easy or hard control flow) → **escape hatches + honesty table**.

## Pre-mortem (m3-selection-r3): "2027-04 bat2ps failed"

Parity claim collapsed on real scripts / LLM converters felt good enough / corpus false confidence / locale broke byte-diff / scope creep → all five mitigations are ADR-003 binding conditions (see README).

## Score: 78/105 (round-3 winner)

Demand 3×5 | Gap 4×4 | Feas 4×4 | Value 4×3 | Maint 2×2 | Dist 3×2 | Fit 5×1.
