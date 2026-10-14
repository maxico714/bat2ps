@echo off
set MODE=prod
if "%MODE%"=="dev" (
  echo dev-mode
) else (
  echo prod-mode
)
