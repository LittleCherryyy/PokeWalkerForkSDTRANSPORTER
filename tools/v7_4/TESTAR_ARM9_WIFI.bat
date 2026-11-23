@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" (
  echo Arraste seu backup .nds original de HeartGold ou SoulSilver para este arquivo BAT.
  echo O programa somente le o arquivo e nunca modifica sua ROM.
  pause
  exit /b 2
)
set "SCRIPT=%~dp0arm9_runtime_reconstruction.py"
set "REPORT=%~dp0wifi_arm9_runtime_report.json"
where py >nul 2>nul
if errorlevel 1 (
  python "%SCRIPT%" "%~1" --output "%REPORT%"
) else (
  py -3 "%SCRIPT%" "%~1" --output "%REPORT%"
)
if errorlevel 1 (
  echo.
  echo A descompactacao ARM9 falhou de modo seguro. Sua ROM nao foi alterada.
  echo Envie o texto do erro para continuar o desenvolvimento.
  pause
  exit /b 2
)
echo.
echo RELATORIO GERADO: "%REPORT%"
echo Envie somente o JSON; nunca a ROM nem os saves.
pause
