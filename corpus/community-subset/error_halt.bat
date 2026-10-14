@echo off
if not exist __definitely_missing_xyz_123.tmp (
  echo required-file-missing
  exit /b 5
)
echo unreachable-ok
