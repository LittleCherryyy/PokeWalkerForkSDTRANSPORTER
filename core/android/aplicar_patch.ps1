param([Parameter(Mandatory=$true)][string]$ProjetoAndroid)
$ErrorActionPreference="Stop"
$dest=Join-Path $ProjetoAndroid "app\src\main\java\io\github\sdtransporter\pokewalker"
if (-not (Test-Path $dest)) { throw "Pasta Java nao encontrada: $dest" }
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$bak=Join-Path $ProjetoAndroid "backup_V67_$stamp"
New-Item -ItemType Directory -Path $bak -Force | Out-Null
foreach($name in @('DirectSyncService.java','DirectSyncProtocol.java')) {
  $target=Join-Path $dest $name
  if(-not(Test-Path $target)){throw "Arquivo ausente: $target"}
  Copy-Item -LiteralPath $target -Destination (Join-Path $bak $name) -Force
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination $target -Force
}
Write-Host "Patch V6.7 aplicado. Backup: $bak"
Write-Host "Compile: .\gradlew.bat :app:assembleDebug"
