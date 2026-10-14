@echo off
set V=nope
if not "%V%"=="yes" echo not-works
if not defined NO_SUCH_VAR_XYZZY echo not-defined-works
