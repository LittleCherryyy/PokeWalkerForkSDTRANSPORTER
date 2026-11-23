@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_thread_abi_context.py"
set "REPORT=%~dp0wifi_v81_hgss_thread_abi.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA: nenhuma ROM, save ou arquivo .walker foi alterado.
  echo Envie a mensagem de erro, nao os arquivos .nds.
  pause
  exit /b 2
)
echo.
echo RELATORIO GERADO: "%REPORT%"
echo Envie somente o JSON. Nada precisa ser instalado no DSi.
pause
exit /b 0
:help
echo Arraste as ROMs originais HeartGold.nds e SoulSilver.nds
echo JUNTAS para COMPARAR_ABI_THREADS.bat.
echo Ou use:
echo COMPARAR_ABI_THREADS.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
