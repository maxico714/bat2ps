@echo off
echo typed-line-1 > __bat2ps_type.tmp
echo typed-line-2 >> __bat2ps_type.tmp
type __bat2ps_type.tmp
del __bat2ps_type.tmp
