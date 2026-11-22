@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" (
  echo Arraste seu arquivo .nds ORIGINAL de HeartGold ou SoulSilver para este BAT.
  echo O teste e local, sem internet e nao altera a ROM, save ou .walker.
  pause
  exit /b 2
)
set "SCRIPT=%~dp0hgss_wifi_call_targets.py"
set "REPORT=%~dp0wifi_calls_%~n1.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo ERRO. Os bytes da ROM nao foram modificados.
  echo Envie uma foto do erro; nao envie a ROM.
  pause
  exit /b 2
)
echo.
echo RESULTADO GERADO: "%REPORT%"
echo Envie somente este JSON.
echo Repita o teste com o outro jogo.
pause
