@echo off
setlocal
set SCOPED_INNER=hello
echo %SCOPED_INNER%
endlocal
echo scope-closed
