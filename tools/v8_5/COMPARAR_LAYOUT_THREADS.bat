@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_thread_info_layout_audit.py"
set "REPORT=%~dp0wifi_v85_hgss_thread_layout.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo Falha segura: ROMs, .sav e .walker nao foram alterados.
  echo Envie somente a mensagem de erro; nunca envie ROMs do jogo.
  pause
  exit /b 2
)
echo.
echo RELATORIO: "%REPORT%"
echo Envie somente este JSON. Nenhum arquivo novo para DSi ou Android.
pause
exit /b 0
:help
echo Selecione seus backups originais HeartGold.nds e SoulSilver.nds.
echo Arraste OS DOIS arquivos simultaneamente para este BAT.
echo Alternativa: COMPARAR_LAYOUT_THREADS.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
