# ADR-002 — Emitter strategy: native core + cmd passthrough (2026-10-14)

- **Context:** byte-identical stdout for `dir/copy/type/sort` output is unreachable
  with reimplementation; `||`/`&&` exit codes follow cmd's register rules.
- **Decision:** control flow + state (`if/for/goto/call/exit/echo/set/cd/shift`)
  emit native PowerShell 5.1 in the same process (live `$LASTEXITCODE`);
  externals/pipes/complex redirects run via `cmd /d /c` (parity by
  construction); `&&`/`||` chains emit natively against the live register
  (verified: `dir-missing || echo fb` exits 1 on cmd).
- **Verified cmd semantics baked in:** `if errorlevel` is `-ge`; `echo/set`
  preserve ERRORLEVEL; `set /a` is silent with truncating `/`; `else`
  binds same-line only; echo/set keep verbatim blanks.
- **Consequences:** translators stay small; translators must never reimplement
  OS-defined output. Rejected: pure-PS reimplementation (diverges),
  whole-line `cmd /c` for chains (breaks `||` exit parity).
