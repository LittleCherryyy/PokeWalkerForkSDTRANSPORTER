@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" (
  echo Arraste seu backup local de HeartGold/SoulSilver .nds para este BAT.
  echo Ou use: python hgss_wifi_abi_audit.py "C:\caminho\jogo.nds" --output wifi_abi_report.json
  pause
  exit /b 2
)
set "SCRIPT=%~dp0hgss_wifi_abi_audit.py"
set "REPORT=%~dp0wifi_abi_report.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" --output "%REPORT%"
)
if errorlevel 1 (
  echo FALHA. O arquivo .nds nao foi modificado.
  pause
  exit /b 2
)
echo.
echo RELATORIO CRIADO: "%REPORT%"
echo Envie apenas o arquivo JSON. Nao envie sua ROM.
pause
