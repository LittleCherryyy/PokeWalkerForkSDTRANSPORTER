@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_register_provenance.py"
set "REPORT=%~dp0wifi_v91_hgss_register_provenance.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA: ROMs, saves e Pokewalker nao foram alterados.
  echo Envie SOMENTE a mensagem de erro, nunca as ROMs.
  pause
  exit /b 2
)
echo.
echo RELATORIO: "%REPORT%"
echo Envie SOMENTE o JSON. Nenhum arquivo deve ir para o DSi.
pause
exit /b 0
:help
echo Selecione os dois backups ORIGINAIS USA Rev0,
echo HeartGold.nds e SoulSilver.nds, e arraste ambos para este BAT.
echo Alternativa: COMPARAR_ORIGEM_REGISTRADORES.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
