@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_arm9_thread_trace_windows.py"
set "REPORT=%~dp0wifi_v90_hgss_scheduler_windows.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA. Nenhuma ROM, save ou arquivo .walker foi alterado.
  echo Envie somente a mensagem de erro. Nao compartilhe ROMs.
  pause
  exit /b 2
)
echo.
echo RELATORIO V9.0: "%REPORT%"
echo Envie apenas o arquivo JSON. Nenhum arquivo novo para o DSi.
pause
exit /b 0
:help
echo Selecione seus backups ORIGINAIS HeartGold.nds e SoulSilver.nds
echo e arraste OS DOIS para COMPARAR_JANELAS_ARM9.bat.
echo Alternativa: COMPARAR_JANELAS_ARM9.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
