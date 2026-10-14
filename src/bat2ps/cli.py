"""CLI: bat2ps convert | verify | harness | doctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __profile_version__, __version__
from .errors import Bat2PsError


def _cmd_convert(args: argparse.Namespace) -> int:
    from .emitter import convert, partial_stub

    src = Path(args.bat)
    if not src.is_file():
        print(f"error: file not found: {src}", file=sys.stderr)
        return 3
    try:
        text = src.read_bytes().decode("utf-8-sig")
    except OSError as e:
        print(f"error: cannot read {src}: {e}", file=sys.stderr)
        return 3
    try:
        ps1 = convert(text, source_name=src.name)
    except Bat2PsError as e:
        if args.allow_partial:
            stub = partial_stub(src.name, e.rule_id, e.message, e.lineno)
            if args.output:
                Path(args.output).write_text(stub, encoding="utf-8")
            else:
                sys.stdout.write(stub)
            print(f"warning: partial conversion: {e}", file=sys.stderr)
            return 0
        print(str(e), file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_text(ps1, encoding="utf-8")
    else:
        sys.stdout.write(ps1)
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    from .harness import verify_pair, verify_source

    bat = Path(args.bat)
    if not bat.is_file():
        print(f"error: file not found: {bat}", file=sys.stderr)
        return 3
    res = verify_pair(bat, Path(args.against)) if args.against else verify_source(bat)
    if res.error and res.parity_stdout == "skip":
        print(res.error, file=sys.stderr)
        return 2 if res.unsupported else 3
    ok = res.parity_stdout == "pass" and res.parity_exit == "pass"
    print(
        f"{bat.name}: stdout={res.parity_stdout} exit={res.parity_exit} "
        f"(cmd={res.cmd_exit} ps={res.ps_exit})"
    )
    if res.first_diff_offset is not None:
        print(f"first diff at offset {res.first_diff_offset}")
        print("--- cmd ---")
        print(res.cmd_stdout[:2000])
        print("--- ps1 ---")
        print(res.ps_stdout[:2000])
    return 0 if ok else 1


def _cmd_harness(args: argparse.Namespace) -> int:
    from .harness import run_corpus, write_report

    corpus = Path(args.corpus)
    if not corpus.is_dir():
        print(f"error: corpus dir not found: {corpus}", file=sys.stderr)
        return 3
    report = run_corpus(corpus, Path(args.workdir) if args.workdir else None)
    md = write_report(report, Path(args.json) if args.json else None)
    if not args.quiet:
        print(md)
    print(
        f"harness: {report['passed']}/{report['total']} passed "
        f"({report['failed']} failed, {report['skipped']} skipped)"
    )
    if int(report["passed"]) < args.min_pass:
        print(f"harness: {report['passed']} passed < required {args.min_pass}", file=sys.stderr)
        return 1
    if int(report["failed"]) > 0:
        return 1
    return 0


def _cmd_doctor(_args: argparse.Namespace) -> int:
    from .doctor import main as doctor_main

    return doctor_main()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="bat2ps",
        description="Batch to PowerShell transpiler with parity harness (profile v0.1).",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__} (profile {__profile_version__})",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="transpile a .bat file to .ps1")
    c.add_argument("bat", help="input .bat file")
    c.add_argument("-o", "--output", default=None, help="output .ps1 (default: stdout)")
    c.add_argument("--profile", default="v0.1", help="batch profile version (only v0.1)")
    c.add_argument(
        "--allow-partial",
        action="store_true",
        help="on out-of-profile input, emit a fail-loud stub "
        "(Write-Error 'unsupported: BPxxx'; exit 2) instead of failing",
    )
    c.set_defaults(func=_cmd_convert)

    v = sub.add_parser("verify", help="convert + differential-verify one file")
    v.add_argument("bat", help="input .bat file")
    v.add_argument("--against", default=None, help="existing .ps1 to compare (skip convert)")
    v.set_defaults(func=_cmd_verify)

    h = sub.add_parser("harness", help="differential-verify a corpus directory")
    h.add_argument("corpus", help="directory of .bat files")
    h.add_argument("--json", default=None, help="write JSON report here")
    h.add_argument("--min-pass", type=int, default=0)
    h.add_argument("--workdir", default=None)
    h.add_argument("--quiet", action="store_true")
    h.set_defaults(func=_cmd_harness)

    d = sub.add_parser("doctor", help="self-check tools and oracle")
    d.set_defaults(func=_cmd_doctor)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
