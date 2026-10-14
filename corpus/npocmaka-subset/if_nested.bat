@echo off
set A=1
set B=2
if "%A%"=="1" if "%B%"=="2" echo both-true
if "%A%"=="1" if "%B%"=="9" echo bad-nest
