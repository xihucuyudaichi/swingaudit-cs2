$ErrorActionPreference = 'Stop'
$roundProject = $PSScriptRoot
$roundPython = (Get-Command python).Source
$roundNode = (Get-Command node).Source
$roundLogDir = Join-Path $roundProject 'verification'
New-Item -ItemType Directory -Path $roundLogDir -Force | Out-Null
if (-not (Get-NetTCPConnection -LocalPort 5188 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $roundPython -ArgumentList @('backend/server.py') -WorkingDirectory $roundProject -WindowStyle Hidden -RedirectStandardOutput (Join-Path $roundLogDir 'backend.log') -RedirectStandardError (Join-Path $roundLogDir 'backend-error.log')
}
if (-not (Get-NetTCPConnection -LocalPort 5177 -State Listen -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath $roundNode -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1') -WorkingDirectory $roundProject -WindowStyle Hidden -RedirectStandardOutput (Join-Path $roundLogDir 'frontend.log') -RedirectStandardError (Join-Path $roundLogDir 'frontend-error.log')
}
Write-Output 'ROUND: http://127.0.0.1:5177/  |  backend: http://127.0.0.1:5188/'
