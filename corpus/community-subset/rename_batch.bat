@echo off
echo data > __bat2ps_rn_old.tmp
for %%f in (__bat2ps_rn_old.tmp) do echo base=%%~nf ext=%%~xf
del __bat2ps_rn_old.tmp
