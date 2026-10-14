@echo off
if "%1"=="deploy" goto do_deploy
if "%1"=="rollback" goto do_rollback
echo usage-default
goto :eof
:do_deploy
echo deploying
goto :eof
:do_rollback
echo rolling-back
goto :eof
