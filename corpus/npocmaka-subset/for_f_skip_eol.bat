@echo off
echo skipme > __bat2ps_fskip.tmp
echo ;commented >> __bat2ps_fskip.tmp
echo keep1 keep2 >> __bat2ps_fskip.tmp
for /f "skip=1 tokens=1" %%a in (__bat2ps_fskip.tmp) do echo kept=%%a
del __bat2ps_fskip.tmp
