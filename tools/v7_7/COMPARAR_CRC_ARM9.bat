@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_wifi_live_crc_reference.py"
set "REPORT=%~dp0wifi_v77_arm9_crc_reference.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" "%~2" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo ERRO SEGURO: nenhum arquivo .nds, .sav ou .walker foi alterado.
  echo Envie o texto da mensagem de erro e NAO suas ROMs.
  pause
  exit /b 2
)
echo.
echo RELATORIO CRIADO: "%REPORT%"
echo Envie somente o JSON junto com uma foto da tela V7.7 do DSi.
pause
exit /b 0
:help
echo Selecione o HeartGold.nds e o SoulSilver.nds no Explorador do Windows
echo e arraste OS DOIS para COMPARAR_CRC_ARM9.bat.
echo Ou use:
echo COMPARAR_CRC_ARM9.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
