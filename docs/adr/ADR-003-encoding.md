# ADR-003 — Text encoding: CRLF batch in, BOM-marked UTF-8 out (2026-10-14)

- **Context:** L4 clean-clone run exposed two real failures: (1) Windows
  PowerShell 5.1 reads BOM-less `.ps1` with the system ANSI codepage, so
  non-ASCII output mojibakes (`‰` parse error); (2) `cmd` under
  `chcp 65001` mis-sniffs LF-only UTF-8 batch files (reads fragments as
  UTF-16).
- **Decision:** all `.bat` fixtures ship CRLF (`.gitattributes` enforces
  `*.bat text eol=crlf`); every `.ps1` we write (harness temp, `convert -o`)
  is UTF-8 **with BOM**; `%VAR%`/`!VAR!`/arithmetic names accept Unicode
  letters.
- **Consequences:** unicode fixture passes for real (non-empty identical
  output both sides) instead of a vacuous double-crash pass. User-supplied
  `--against` files remain the user's responsibility (documented).
