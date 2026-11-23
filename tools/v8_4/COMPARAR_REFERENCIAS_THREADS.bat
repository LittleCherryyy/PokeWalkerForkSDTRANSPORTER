@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_thread_flag_xrefs.py"
set "REPORT=%~dp0wifi_v84_thread_flag_xrefs.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo Falha segura: ROMs, saves e Pokewalker NAO foram alterados.
  echo Envie apenas a mensagem de erro; nunca envie as ROMs.
  pause
  exit /b 2
)
echo.
echo Relatorio gerado: "%REPORT%"
echo Envie somente o JSON. Nada precisa ser instalado no DSi.
pause
exit /b 0
:help
echo Selecione seus dois arquivos HeartGold.nds e SoulSilver.nds
echo e arraste ambos para COMPARAR_REFERENCIAS_THREADS.bat.
pause
exit /b 2
