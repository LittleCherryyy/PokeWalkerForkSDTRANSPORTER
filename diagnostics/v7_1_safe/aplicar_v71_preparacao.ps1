param([Parameter(Mandatory=$true)][string]$Bootstrap)
$ErrorActionPreference = "Stop"
$dest = Join-Path $Bootstrap "retail\common\source\walker_hgss_net.c"
$src = Join-Path $PSScriptRoot "patch\walker_hgss_net.c"
if (!(Test-Path $dest)) { throw "Arquivo nao encontrado: $dest" }
$actual = (Get-FileHash $dest -Algorithm SHA256).Hash.ToUpperInvariant()
$expected = "C302FCF212440A862EB5260BCB8A295894441BC2EA2B07667ACF79574811A64C"
$updated = "C80388ECCD10FC13269FF03E35A1ADE7B3A6BC7063808A992D48F3EA5FDB8B65"
if ($actual -eq $updated) { Write-Host "V7.1 preflight ja aplicado. Nenhuma alteracao."; exit 0 }
if ($actual -ne $expected) { throw "Versao diferente do fonte V18 analisado. Nada foi alterado. Hash atual: $actual" }
$backup = "$dest.bak_V71_$(Get-Date -Format yyyyMMdd-HHmmss)"
Copy-Item -LiteralPath $dest -Destination $backup
Copy-Item -LiteralPath $src -Destination $dest
$after = (Get-FileHash $dest -Algorithm SHA256).Hash.ToUpperInvariant()
if ($after -ne $updated) { Copy-Item -LiteralPath $backup -Destination $dest -Force; throw "Falha de verificacao apos copia; original restaurado." }
Write-Host "V7.1 preflight aplicado com backup: $backup"
Write-Host "ATENCAO: Nao ha PING dentro do HeartGold; nao atualizar o SD ainda."
