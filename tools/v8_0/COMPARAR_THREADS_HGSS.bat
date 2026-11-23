@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_thread_callsite_audit.py"
set "REPORT=%~dp0wifi_v80_hgss_threads.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo ERRO SEGURO: ROMs, saves e .walker nao foram alterados.
  echo Envie o erro exibido; nunca envie a ROM.
  pause
  exit /b 2
)
echo.
echo RELATORIO: "%REPORT%"
echo Envie somente o JSON. Nenhum arquivo vai para o DSi nesta fase.
pause
exit /b 0
:help
echo Arraste HeartGold.nds e SoulSilver.nds juntos para este BAT.
echo Alternativa: COMPARAR_THREADS_HGSS.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
