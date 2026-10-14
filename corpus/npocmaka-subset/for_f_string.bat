@echo off
for /f "tokens=1,2 delims=," %%a in ("red,green,blue") do echo first=%%a second=%%b
