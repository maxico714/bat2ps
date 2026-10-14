@echo off
:argloop
if "%1"=="" goto argdone
echo arg=[%1]
shift
goto argloop
:argdone
echo args-done
