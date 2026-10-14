"""Differential parity harness: run .bat under cmd vs .ps1 under PowerShell.

Parity contract (v0.1):
1. Both processes terminate (timeout-bounded).
2. Normalised stdout bytes are equal (CRLF/CR -> LF; trailing-newline
   insensitive comparison is NOT applied — strict equality after EOL fold).
3. Exit codes are equal.
4. stderr is compared non-blocking (warn-level only).

Pinned env: ``cmd /d`` (no AutoRun), ``chcp 65001`` before the batch,
``powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File``.
Both runs share cwd = the script's directory and stdin = DEVNULL so that
``pause``-style reads terminate instead of hanging.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import __version__
from .emitter import convert

PROFILE = "v0.1"
TIMEOUT_S = 60


@dataclass
class CaseResult:
    file: str
    profile: str = PROFILE
    supported: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    parity_stdout: str = "skip"  # pass | fail | skip
    parity_exit: str = "skip"  # pass | fail | skip
    cmd_exit: int | None = None
    ps_exit: int | None = None
    cmd_stdout: str = ""
    ps_stdout: str = ""
    stderr_note: str = ""
    first_diff_offset: int | None = None
    error: str = ""
    elapsed_ms: int = 0


def normalize_stdout(data: bytes) -> str:
    """Decode UTF-8 (BOM-tolerant, replace errors) and fold EOLs to LF."""
    text = data.decode("utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def find_first_diff(a: str, b: str) -> int | None:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return n
    return None


def _powershell_exe() -> str:
    for cand in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
        # resolved via PATH at spawn time; prefer classic powershell.exe
        return cand
    return "powershell.exe"  # pragma: no cover


def run_bat(bat_path: Path, cwd: Path) -> tuple[bytes, bytes, int]:
    """Run a .bat under cmd.exe with pinned codepage. Returns (out, err, code).

    A tiny wrapper pins ``chcp 65001`` inside the SAME cmd instance (a
    separate ``chcp`` process would not persist) while avoiding cmd's fragile
    ``/c "..."`` nested-quote parsing: the wrapper is invoked by short name.
    """
    wrapper = cwd / (bat_path.stem + ".__bat2ps_run.bat")
    wrapper.write_text(f'@chcp 65001>nul\r\n@call "{bat_path.name}"\r\n', encoding="ascii")
    try:
        proc = subprocess.run(
            ["cmd", "/d", "/c", "call", wrapper.name],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=TIMEOUT_S,
        )
    finally:
        with contextlib.suppress(OSError):
            wrapper.unlink()
    return proc.stdout, proc.stderr, proc.returncode


def run_ps1(
    ps1_path: Path, cwd: Path, extra_args: list[str] | None = None
) -> tuple[bytes, bytes, int]:
    """Run a .ps1 under PowerShell with a clean profile. Returns (out, err, code)."""
    exe = _powershell_exe()
    cmd = [
        exe,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ps1_path),
    ]
    if extra_args:
        cmd += extra_args
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=TIMEOUT_S,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"powershell executable not found ({exe}): {e}") from e
    return proc.stdout, proc.stderr, proc.returncode


def verify_pair(bat_path: Path, ps1_path: Path, cwd: Path | None = None) -> CaseResult:
    """Convert-free differential check of an existing .bat/.ps1 pair."""
    res = CaseResult(file=bat_path.name)
    workdir = cwd or bat_path.parent
    bat_abs = bat_path.resolve()
    ps1_abs = ps1_path.resolve()
    t0 = time.monotonic()
    try:
        bout, berr, bcode = run_bat(bat_abs, workdir)
    except subprocess.TimeoutExpired:
        res.error = "cmd timeout"
        res.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return res
    try:
        pout, perr, pcode = run_ps1(ps1_abs, workdir)
    except subprocess.TimeoutExpired:
        res.error = "powershell timeout"
        res.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return res
    except RuntimeError as e:
        res.error = str(e)
        res.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return res
    return _compare(res, bout, berr, bcode, pout, perr, pcode, t0)


def verify_source(bat_path: Path, workdir: Path | None = None) -> CaseResult:
    """Convert *bat_path* with the transpiler, run both, compare."""
    from .errors import Bat2PsError

    res = CaseResult(file=bat_path.name)
    t0 = time.monotonic()
    try:
        text = bat_path.read_bytes().decode("utf-8-sig")
    except OSError as e:
        res.error = f"read error: {e}"
        return res
    try:
        ps1 = convert(text, source_name=bat_path.name)
    except Bat2PsError as e:
        res.unsupported = [e.rule_id]
        res.error = str(e)
        res.parity_stdout = "skip"
        res.parity_exit = "skip"
        res.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return res
    cwd = workdir or bat_path.parent
    tmp_ps1 = (cwd / (bat_path.stem + ".__bat2ps_verify.ps1")).resolve()
    try:
        tmp_ps1.write_text(ps1, encoding="utf-8")
        try:
            bout, berr, bcode = run_bat(bat_path.resolve(), cwd)
        except subprocess.TimeoutExpired:
            res.error = "cmd timeout"
            return res
        try:
            pout, perr, pcode = run_ps1(tmp_ps1, cwd)
        except subprocess.TimeoutExpired:
            res.error = "powershell timeout"
            return res
        except RuntimeError as e:
            res.error = str(e)
            return res
        return _compare(res, bout, berr, bcode, pout, perr, pcode, t0)
    finally:
        with contextlib.suppress(OSError):
            tmp_ps1.unlink()


def _compare(
    res: CaseResult,
    bout: bytes,
    berr: bytes,
    bcode: int,
    pout: bytes,
    perr: bytes,
    pcode: int,
    t0: float,
) -> CaseResult:
    bn = normalize_stdout(bout)
    pn = normalize_stdout(pout)
    res.cmd_stdout = bn
    res.ps_stdout = pn
    res.cmd_exit = bcode
    res.ps_exit = pcode
    res.parity_stdout = "pass" if bn == pn else "fail"
    res.parity_exit = "pass" if bcode == pcode else "fail"
    if res.parity_stdout == "fail":
        res.first_diff_offset = find_first_diff(bn, pn)
    # stderr is warn-level: record presence, never fail parity on it.
    if berr.strip() or perr.strip():
        res.stderr_note = (
            f"cmd_stderr={len(berr)}B ps_stderr={len(perr)}B "
            "(informational; stderr does not affect parity)"
        )
    res.elapsed_ms = int((time.monotonic() - t0) * 1000)
    return res


def run_corpus(corpus_dir: Path, workdir: Path | None = None) -> dict[str, Any]:
    """Convert+verify every ``*.bat`` in *corpus_dir* (sorted, sequential)."""
    bats = sorted(corpus_dir.glob("*.bat"))
    cases: list[dict[str, Any]] = []
    for bat in bats:
        res = verify_source(bat, workdir)
        cases.append(asdict(res))
    passed = sum(1 for c in cases if c["parity_stdout"] == "pass" and c["parity_exit"] == "pass")
    failed = sum(1 for c in cases if c["parity_stdout"] == "fail" or c["parity_exit"] == "fail")
    skipped = len(cases) - passed - failed
    return {
        "tool": f"bat2ps {__version__}",
        "profile": PROFILE,
        "corpus": str(corpus_dir),
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "cases": cases,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# bat2ps harness report (profile {report['profile']})",
        "",
        f"Corpus: `{report['corpus']}` — total {report['total']}, "
        f"passed {report['passed']}, failed {report['failed']}, "
        f"skipped {report['skipped']}.",
        "",
        "| file | stdout | exit | cmd_exit | ps_exit | note |",
        "|---|---|---|---|---|---|",
    ]
    for c in report["cases"]:
        note = str(c.get("error") or c.get("stderr_note") or "")
        lines.append(
            f"| {c['file']} | {c['parity_stdout']} | {c['parity_exit']} | "
            f"{c['cmd_exit']} | {c['ps_exit']} | {note} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], json_path: Path | None) -> str:
    """Write JSON (if path given) stripping bulky stdout; return markdown."""
    md = render_markdown(report)
    if json_path is not None:
        slim = dict(report)
        slim_cases = []
        for c in report["cases"]:
            d = dict(c)
            d.pop("cmd_stdout", None)
            d.pop("ps_stdout", None)
            slim_cases.append(d)
        slim["cases"] = slim_cases
        json_path.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="bat2ps-harness")
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--json", dest="json_path", type=Path, default=None)
    ap.add_argument("--min-pass", type=int, default=0)
    ap.add_argument("--workdir", type=Path, default=None)
    args = ap.parse_args(argv)
    if not args.corpus.is_dir():
        print(f"error: corpus dir not found: {args.corpus}", file=sys.stderr)
        return 3
    report = run_corpus(args.corpus, args.workdir)
    md = write_report(report, args.json_path)
    print(md)
    passed = int(report["passed"])
    if passed < args.min_pass:
        print(f"harness: {passed} passed < required {args.min_pass}", file=sys.stderr)
        return 1
    if int(report["failed"]) > 0:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
