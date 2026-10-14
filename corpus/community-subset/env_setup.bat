@echo off
setlocal
set APP_ENV=staging
set APP_PORT=8080
echo env=%APP_ENV% port=%APP_PORT%
endlocal
if defined APP_ENV (echo leak-bad) else (echo no-leak-good)
