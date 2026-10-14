@echo off
echo w1 > __bat2ps_wc_a.tmp
echo w2 > __bat2ps_wc_b.tmp
for %%x in (__bat2ps_wc_*.tmp) do echo found=%%x
del __bat2ps_wc_a.tmp
del __bat2ps_wc_b.tmp
