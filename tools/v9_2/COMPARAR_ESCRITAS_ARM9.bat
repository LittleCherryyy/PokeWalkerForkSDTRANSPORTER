@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_store_value_backtrace.py"
set "REPORT=%~dp0wifi_v92_hgss_store_value_backtrace.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo FALHA SEGURA: ROM, save, Pokewalker e DSi nao foram alterados.
  echo Envie SOMENTE a mensagem de erro, sem compartilhar as ROMs.
  pause
  exit /b 2
)
echo.
echo RELATORIO V9.2: "%REPORT%"
echo Envie somente o JSON; nao substitua nada no DSi.
pause
exit /b 0
:help
echo Selecione os backups originais USA Rev0 HeartGold.nds e SoulSilver.nds.
echo Arraste os dois arquivos sobre COMPARAR_ESCRITAS_ARM9.bat.
echo Alternativa: COMPARAR_ESCRITAS_ARM9.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
