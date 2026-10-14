@echo off
setlocal enabledelayedexpansion
set COUNT=0
for %%x in (a b c) do (
  set /a COUNT+=1
  echo !COUNT!:%%x
)
endlocal
