@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_thread_scheduler_refs.py"
set "REPORT=%~dp0wifi_v82_hgss_scheduler_refs.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo Falha segura: nenhum .nds, .sav ou .walker foi modificado.
  echo Envie a mensagem de erro; nao envie os arquivos do jogo.
  pause
  exit /b 2
)
echo.
echo RELATORIO CRIADO: "%REPORT%"
echo Compartilhe somente este arquivo JSON.
echo Nao precisa alterar o DSi nem o Android.
pause
exit /b 0
:help
echo Selecione seus backups originais HeartGold.nds e SoulSilver.nds
echo e arraste OS DOIS para COMPARAR_ESTADO_THREADS.bat.
echo Ou execute: COMPARAR_ESTADO_THREADS.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
