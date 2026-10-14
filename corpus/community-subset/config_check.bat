@echo off
if defined WINDIR (
  echo config-root-ok
) else (
  echo config-missing
  exit /b 1
)
if defined NO_SUCH_VAR_XYZZY (
  echo unexpected
) else (
  echo optional-absent-ok
)
