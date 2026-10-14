@echo off
echo one:two:three > __bat2ps_ffile.tmp
echo four:five >> __bat2ps_ffile.tmp
for /f "tokens=2 delims=:" %%b in (__bat2ps_ffile.tmp) do echo tok=%%b
del __bat2ps_ffile.tmp
