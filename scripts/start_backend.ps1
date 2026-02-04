Push-Location 'C:\Users\gebruiker\Desktop\mijn_api'
$pids = netstat -ano | Select-String ':8000' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Unique
if ($pids) {
    foreach ($p in $pids) {
        Write-Host "Killing process $p using port 8000"
        taskkill /PID $p /F
    }
} else {
    Write-Host 'No process found on port 8000'
}
Start-Sleep -s 1
$env:JWT_SECRET_KEY='devsecret'
$env:DATA_DIR='C:\Users\gebruiker\Desktop\mijn_api'
$env:ALLOW_DEBUG='1'
Start-Process -NoNewWindow -FilePath 'C:\Users\gebruiker\Desktop\mijn_api\venv2\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000' -PassThru
