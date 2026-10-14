@echo off
echo marker > __bat2ps_exist_probe.tmp
if exist __bat2ps_exist_probe.tmp echo exists-yes
del __bat2ps_exist_probe.tmp
if not exist __bat2ps_exist_probe.tmp echo gone-yes
