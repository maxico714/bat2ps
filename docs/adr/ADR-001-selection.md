# ADR-001 — Why bat2ps (2026-10-12, round-3 selection)

- **Context:** 10–15 candidate tools scored on demand/gap/feasibility/value/maintainability/distribution/fit.
- **Evidence:** 5+ independent sources agree no mature OSS batch→PS *script* transpiler exists
  (Inedo guide, forums.powershell.org/t/21609 with 13,404 views, SuperUser 851610 with
  66,805 views); demand hook honestly capped at 3/5 (migration help wanted, not proven buyers).
- **Decision:** build `bat2ps` (score 78/105). Gap class A. Differentiator: the only
  converter that *proves* parity by differential execution (harness as product).
- **Runner-ups/implications:** LLM converters own first-draft UX — position as "unverified";
  npocmaka demos are not production scripts — second corpus required before coverage claims.
- **Status:** accepted; binding conditions 1–5 in README (profile first, harness-led,
  second corpus, escape hatches, V1_SCOPE_CAP).
