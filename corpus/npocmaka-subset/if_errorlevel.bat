@echo off
dir __no_such_file_xyyasdf.txt >nul 2>&1
if errorlevel 1 echo failed-as-expected
if errorlevel 2 echo wrong-level
cmd /d /c exit 2
if errorlevel 1 echo ge-semantics-ok
if errorlevel 3 echo wrong-level-3
echo done
