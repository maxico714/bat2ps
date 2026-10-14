@echo off
mkdir __bat2ps_cdprobe 2>nul
cd __bat2ps_cdprobe
echo inner-marker > inner.txt
cd ..
type __bat2ps_cdprobe\inner.txt
del __bat2ps_cdprobe\inner.txt
rmdir __bat2ps_cdprobe
echo dirs-ok
