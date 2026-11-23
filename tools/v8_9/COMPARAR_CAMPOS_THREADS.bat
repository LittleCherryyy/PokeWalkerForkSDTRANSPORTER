@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_scheduler_field_xrefs.py"
set "REPORT=%~dp0wifi_v89_hgss_thread_field_xrefs.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA: nenhuma ROM ou arquivo de save foi alterado.
  echo Envie somente a mensagem de erro, nao os arquivos .nds.
  pause
  exit /b 2
)
echo.
echo RELATORIO: "%REPORT%"
echo Compartilhe apenas este JSON. Nao instale nada no DSi ou Android.
pause
exit /b 0
:help
echo Selecione seus backups ORIGINAIS HeartGold.nds e SoulSilver.nds
echo e arraste OS DOIS para COMPARAR_CAMPOS_THREADS.bat.
echo Ou rode: COMPARAR_CAMPOS_THREADS.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
