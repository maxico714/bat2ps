@echo off
rem simulated deploy: stage files then verify
echo v1-content > __bat2ps_dep_src.tmp
if exist __bat2ps_dep_src.tmp (
  copy __bat2ps_dep_src.tmp __bat2ps_dep_dst.tmp >nul
  if exist __bat2ps_dep_dst.tmp (
    echo deploy-ok
  ) else (
    echo deploy-missing
  )
) else (
  echo no-source
)
del __bat2ps_dep_src.tmp
del __bat2ps_dep_dst.tmp
