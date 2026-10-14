@echo off
set V=Hello
if /i "%V%"=="hello" echo ci-true
if "%V%"=="hello" echo cs-false
