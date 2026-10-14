@echo off
echo row1 > __bat2ps_app.tmp
echo row2 >> __bat2ps_app.tmp
echo row3 >> __bat2ps_app.tmp
type __bat2ps_app.tmp
del __bat2ps_app.tmp
