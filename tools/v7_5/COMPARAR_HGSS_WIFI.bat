@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto how
if "%~2"=="" goto how
set "SCRIPT=%~dp0hgss_wifi_call_targets.py"
set "REPORT=%~dp0wifi_calls_HGSS_comparativo.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" --compare "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" --compare "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA: nenhuma ROM, save ou arquivo walker foi modificado.
  echo Envie a mensagem de erro, sem enviar as ROMs.
  pause
  exit /b 2
)
echo.
echo SUCESSO: "%REPORT%"
echo Envie SOMENTE o JSON.
pause
exit /b 0
:how
echo Selecione HeartGold.nds e SoulSilver.nds simultaneamente e arraste
echo OS DOIS arquivos para este BAT.
echo Alternativa: COMPARAR_HGSS_WIFI.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
