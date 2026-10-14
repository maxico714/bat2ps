@echo off
set /a ACC=0
set OP=add
if "%OP%"=="add" goto op_add
goto op_done
:op_add
set /a ACC=40+2
goto op_done
:op_done
echo acc=%ACC%
