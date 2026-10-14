@echo off
echo n,v > __bat2ps_csv.tmp
echo ada,36 >> __bat2ps_csv.tmp
echo bob,29 >> __bat2ps_csv.tmp
for /f "skip=1 tokens=1,2 delims=," %%a in (__bat2ps_csv.tmp) do echo name=%%a age=%%b
del __bat2ps_csv.tmp
