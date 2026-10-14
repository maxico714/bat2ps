@echo off
call :worker
echo back-in-main
goto :eof
:worker
echo inside-sub
goto :eof
