@echo off
if defined WINDIR echo windir-yes
if defined NO_SUCH_VAR_XYZZY (echo bad) else (echo else-taken)
