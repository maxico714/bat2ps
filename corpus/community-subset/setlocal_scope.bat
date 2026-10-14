@echo off
set TOPLEVEL=outer
setlocal
set TOPLEVEL=inner
set ONLY_INNER=yes
echo %TOPLEVEL% %ONLY_INNER%
endlocal
echo %TOPLEVEL%
if defined ONLY_INNER (echo leak-bad) else (echo scoped-good)
