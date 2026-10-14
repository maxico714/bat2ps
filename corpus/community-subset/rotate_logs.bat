@echo off
set LOGN=0
:nextlog
set /a LOGN+=1
echo log-entry-%LOGN% > __bat2ps_log%LOGN%.tmp
if %LOGN% lss 3 goto nextlog
for %%f in (__bat2ps_log1.tmp __bat2ps_log2.tmp __bat2ps_log3.tmp) do type %%f
for %%f in (__bat2ps_log1.tmp __bat2ps_log2.tmp __bat2ps_log3.tmp) do del %%f
echo rotate-done
