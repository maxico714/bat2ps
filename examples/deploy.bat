@echo off
rem deploy.bat — realistic sample: stage, verify, report (in-profile only).
setlocal
set APP_ENV=staging
set APP_PORT=8080
echo env=%APP_ENV% port=%APP_PORT%
if defined APP_ENV (
  echo config-ok
) else (
  echo config-missing
  exit /b 1
)
for /l %%i in (1,1,3) do echo step-%%i
endlocal
echo deploy-sample-done
