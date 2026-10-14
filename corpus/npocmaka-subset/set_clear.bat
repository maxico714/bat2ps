@echo off
set SCRATCH_GONE=present
set SCRATCH_GONE=
if defined SCRATCH_GONE (echo still-here) else (echo cleared)
