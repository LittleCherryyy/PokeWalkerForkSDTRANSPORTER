param([Parameter(Mandatory=$true)][string]$Bootstrap)
$ErrorActionPreference = "Stop"
$sourceDir = Join-Path $Bootstrap "retail\cardenginei\arm9_igm\source"
if (-not (Test-Path $sourceDir)) { throw "Nao achei $sourceDir. Informe a pasta bootstrap, nao a pasta retail ou android." }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$backup = Join-Path $Bootstrap ("backup_igm_v70_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($name in @("inGameMenu.c", "inGameMenu.h")) {
    $target = Join-Path $sourceDir $name
    if (-not (Test-Path $target)) { throw "Arquivo original ausente: $target" }
    $expected = if ($name -eq "inGameMenu.c") { "8fe12656b74d0f1077a6bd6db7088274f05667829435df1d89155ae7ae5c3151" } else { "99d9486272e134c164fb11e0dc09ccc493d139656a19c76af35036501f95adb8" }
    $actual = (Get-FileHash -Algorithm SHA256 -Path $target).Hash.ToLower()
    if ($actual -ne $expected) { throw "Origem $name nao corresponde a V18 examinada. Nao alterado." }
    Copy-Item $target (Join-Path $backup $name)
    Copy-Item (Join-Path $here $name) $target -Force
}
Write-Host "Patch V7.0 instalado; backup: $backup"
Write-Host "Build exige devkitARM. Este patch NAO implementa Wi-Fi em jogo ou PING V7.1."
