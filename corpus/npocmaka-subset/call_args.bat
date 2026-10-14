@echo off
call :greet Alice Bob
goto :eof
:greet
echo hi-%1-%2
goto :eof
