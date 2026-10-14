"""--doctor self-check: tool versions, oracle presence, smoke runs."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _exe(name: str) -> str | None:
    return shutil.which(name)


def check() -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    lines.append(f"python: {sys.version.split()[0]}")
    for tool in ("cmd", "powershell"):
        found = _exe(tool) or _exe(tool + ".exe")
        lines.append(f"{tool}: {'found at ' + found if found else 'MISSING'}")
        if not found:
            ok = False
    # cmd exit-code propagation smoke test
    try:
        p = subprocess.run(
            ["cmd", "/d", "/c", "exit /b 42"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=30,
        )
        lines.append(f"cmd exit-propagation: exit={p.returncode} (want 42)")
        if p.returncode != 42:
            ok = False
    except Exception as e:  # noqa: BLE001
        lines.append(f"cmd exit-propagation: FAILED ({e})")
        ok = False
    # powershell exit-code propagation smoke test
    psexe = _exe("powershell") or _exe("powershell.exe") or _exe("pwsh") or _exe("pwsh.exe")
    if psexe:
        try:
            p = subprocess.run(
                [psexe, "-NoProfile", "-NonInteractive", "-Command", "exit 42"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=30,
            )
            lines.append(f"powershell exit-propagation: exit={p.returncode} (want 42)")
            if p.returncode != 42:
                ok = False
        except Exception as e:  # noqa: BLE001
            lines.append(f"powershell exit-propagation: FAILED ({e})")
            ok = False
    # transpile+run smoke test (echo parity)
    try:
        from .emitter import convert
        from .harness import normalize_stdout, run_bat, run_ps1

        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "smoke.bat").write_text("@echo off\necho doctor-ok\n", encoding="utf-8")
            ps1 = convert("@echo off\necho doctor-ok\n", source_name="smoke.bat")
            (d / "smoke.ps1").write_text(ps1, encoding="utf-8")
            bout, _, bcode = run_bat(d / "smoke.bat", d)
            pout, _, pcode = run_ps1(d / "smoke.ps1", d)
            same = normalize_stdout(bout) == normalize_stdout(pout) and bcode == pcode
            lines.append(f"transpile+parity smoke: {'ok' if same else 'MISMATCH'}")
            if not same:
                ok = False
    except Exception as e:  # noqa: BLE001
        lines.append(f"transpile+parity smoke: FAILED ({e})")
        ok = False
    lines.append("profile: v0.1")
    return ok, lines


def main() -> int:
    ok, lines = check()
    for ln in lines:
        print(ln)
    return 0 if ok else 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
