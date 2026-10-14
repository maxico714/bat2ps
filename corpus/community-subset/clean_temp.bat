@echo off
echo junk1 > __bat2ps_clean1.tmp
echo junk2 > __bat2ps_clean2.tmp
for %%f in (__bat2ps_clean1.tmp __bat2ps_clean2.tmp) do del %%f
if not exist __bat2ps_clean1.tmp echo cleaned-1
if not exist __bat2ps_clean2.tmp echo cleaned-2
