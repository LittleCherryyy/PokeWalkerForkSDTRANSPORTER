$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
if (-not (Test-Path -LiteralPath $sdk -PathType Container)) {
    throw "Android SDK nao encontrado em $sdk. Abra SDK Manager no Android Studio."
}
$sdkProp = $sdk.Replace('\','/')
"sdk.dir=$sdkProp" | Set-Content -LiteralPath 'local.properties' -Encoding ASCII
Write-Host "SDK localizado: $sdk" -ForegroundColor Cyan
& .\gradlew.bat clean :app:assembleDebug
if ($LASTEXITCODE -ne 0) {throw "Compilacao Gradle falhou (codigo $LASTEXITCODE)."}
$apk = Join-Path $PSScriptRoot 'app\build\outputs\apk\debug\app-debug.apk'
if (-not (Test-Path -LiteralPath $apk)) {throw "Gradle concluiu mas APK nao encontrado: $apk"}
Write-Host "APK gerado: $apk" -ForegroundColor Green
