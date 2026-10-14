@echo off
echo line-one > __bat2ps_redir.tmp
echo line-two >> __bat2ps_redir.tmp
type __bat2ps_redir.tmp
del __bat2ps_redir.tmp
