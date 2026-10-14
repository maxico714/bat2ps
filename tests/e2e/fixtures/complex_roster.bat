@echo off
setlocal enabledelayedexpansion
echo name,dept> __e2e_roster.tmp
echo ada,eng>> __e2e_roster.tmp
echo bob,ops>> __e2e_roster.tmp
echo cy,eng>> __e2e_roster.tmp
set ENG=0
for /f "skip=1 tokens=1,2 delims=," %%a in (__e2e_roster.tmp) do (
  if "%%b"=="eng" (
    set /a ENG+=1
    echo !ENG!:%%a
  ) else (
    echo other:%%a
  )
)
del __e2e_roster.tmp
if %ENG%==2 (echo eng-ok) else (echo eng-bad)
type nul | find "zzz-no-match" >nul 2>&1 || echo pipe-used
endlocal
