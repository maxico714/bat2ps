@echo off
echo [step] stop
echo [step] start
dir __no_such_svc_xyz >nul 2>&1
if errorlevel 1 (
  echo svc-flagged
) else (
  echo svc-fine
)
echo restart-sim-done
