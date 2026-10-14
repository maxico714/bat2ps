@echo off
set TRIES=0
:tryagain
set /a TRIES+=1
dir __no_such_retry_xyz >nul 2>&1
if errorlevel 1 if %TRIES% lss 3 goto tryagain
echo tried-%TRIES%-times
