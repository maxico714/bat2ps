@echo off
set /a C=0
:again
set /a C+=1
echo iter=%C%
if %C% lss 3 goto again
echo loop-done
