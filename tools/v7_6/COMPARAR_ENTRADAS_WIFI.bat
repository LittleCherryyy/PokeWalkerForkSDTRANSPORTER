@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_wifi_entry_audit.py"
set "REPORT=%~dp0wifi_v76_arm9_entry_comparison.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo Falha segura: as ROMs, saves e arquivos .walker continuam intactos.
  echo Envie o texto do erro. Nao compartilhe sua ROM.
  pause
  exit /b 2
)
echo.
echo Relatorio concluido: "%REPORT%"
echo Envie somente o arquivo JSON.
pause
exit /b 0
:help
echo Arraste simultaneamente as duas ROMs originais de HG e SS para este BAT.
echo Ou execute: COMPARAR_ENTRADAS_WIFI.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
