$root = $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\boostrag-api'; .\.venv\Scripts\Activate.ps1; uvicorn main:app --reload"

Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$root\boostrag-frontend'; npm run dev"

Write-Host "API  -> http://127.0.0.1:8000"
Write-Host "App  -> http://localhost:5173"
