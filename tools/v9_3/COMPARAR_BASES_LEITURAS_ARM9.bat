@echo off
setlocal DisableDelayedExpansion
if "%~1"=="" goto help
if "%~2"=="" goto help
set "SCRIPT=%~dp0hgss_store_address_register_origins.py"
set "REPORT=%~dp0wifi_v93_hgss_source_load_base_origins.json"
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
echo RELATORIO V9.3: "%REPORT%"
echo Envie somente o JSON; nao substitua nada no DSi.
pause
exit /b 0
:help
echo Selecione os backups originais USA Rev0 HeartGold.nds e SoulSilver.nds.
echo Arraste ambos para COMPARAR_BASES_LEITURAS_ARM9.bat.
echo Alternativa: COMPARAR_BASES_LEITURAS_ARM9.bat "HeartGold.nds" "SoulSilver.nds"
pause
exit /b 2
