@echo off
for /l %%i in (1,1,3) do (
  if %%i==2 (
    echo two!
  ) else (
    echo n=%%i
  )
)
