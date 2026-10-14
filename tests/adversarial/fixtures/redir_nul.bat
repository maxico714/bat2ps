@echo off
echo hi >nul
dir __no_such_xyz >nul 2>&1
echo after-nul
