@echo off
dir __no_such_file_zz top-level >nul 2>&1
echo level-is-%ERRORLEVEL%
