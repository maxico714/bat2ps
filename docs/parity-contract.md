# Parity contract v0.1 (frozen 2026-10-14)

A conversion of `x.bat` → `x.ps1` is **verified** iff, in the pinned
environment below:

1. Both processes terminate (60 s timeout each; stdin is DEVNULL so
   `pause`-style reads cannot hang).
2. Normalised stdout bytes are **equal** — normalisation is CRLF/CR → LF
   only (no trimming, no trailing-newline forgiveness).
3. Exit codes are **equal**.
4. stderr is recorded but **never** decides parity (Windows localises
   system error strings; see the locale trap).

## Pinned environment

- Batch side: `cmd /d /c call <wrapper>` where the wrapper runs
  `chcp 65001>nul` then `call "x.bat"` in the **same** instance
  (a separate `chcp` process would not persist; quoting the whole
  command breaks cmd's `/c` quote handling — both verified 2026-10-14).
- PowerShell side: `powershell -NoProfile -NonInteractive
  -ExecutionPolicy Bypass -File x.ps1`. Emitted scripts pin
  `[Console]::OutputEncoding` / `$OutputEncoding` to UTF-8 (no BOM).
- cwd for both runs is the script's directory; runs are sequential.

## Report schema

`bat2ps harness <dir> --json report.json` writes:

```json
{
  "tool": "bat2ps 0.1.0",
  "profile": "v0.1",
  "corpus": "<dir>",
  "total": 64, "passed": 64, "failed": 0, "skipped": 0,
  "cases": [
    {"file": "echo_hello.bat", "profile": "v0.1",
     "supported": [], "unsupported": [],
     "parity": {"stdout": "pass", "exit": "pass"},
     "parity_stdout": "pass", "parity_exit": "pass",
     "cmd_exit": 0, "ps_exit": 0, "first_diff_offset": null,
     "error": "", "elapsed_ms": 123}
  ]
}
```

(Flat `parity_stdout`/`parity_exit` keys are kept for CLI ergonomics;
the nested `parity` object is informational.)

Exit codes: `0` ok / all-pass, `1` parity-fail or below `--min-pass`,
`2` unsupported construct (convert/verify), `3` environment error.

## What parity does NOT cover

- Scripts outside `docs/BATCH_PROFILE.md` (convert refuses loudly).
- Nondeterministic built-ins (`%DATE/%TIME/%RANDOM%`, network, real time).
- stderr bytes (warn-level only).
- Locales other than en-US + codepage 65001.
- `%~nx0`-style name derivatives under temp-file comparison.
