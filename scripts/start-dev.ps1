$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ChromePath = 'C:\Program Files\Google\Chrome\Application\chrome.exe'

Start-Process -FilePath (Join-Path $ProjectRoot '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','api.main:app','--reload','--host','127.0.0.1','--port','8000' -WorkingDirectory $ProjectRoot -WindowStyle Hidden
Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory (Join-Path $ProjectRoot 'frontend') -WindowStyle Hidden
Start-Sleep -Seconds 3
if (Test-Path -LiteralPath $ChromePath) {
    Start-Process -FilePath $ChromePath -ArgumentList 'http://127.0.0.1:5173'
} else {
    Write-Warning 'Google Chrome est introuvable. Ouvrez http://127.0.0.1:5173 manuellement.'
}
