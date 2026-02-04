# Elevated script: shows ownership of port 8000, kills owner PIDs, and starts uvicorn
# This script should be run with Administrator privileges (Start-Process -Verb RunAs).
Push-Location 'C:\Users\gebruiker\Desktop\mijn_api'
Write-Host '=== netstat :8000 (raw) ==='
netstat -ab -o | Select-String ':8000' | ForEach-Object { Write-Host $_ }

# Extract PIDs using netstat -ano (fallback if -ab requires admin)
$pids = netstat -ano | Select-String ':8000' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Unique
if ($pids) {
    foreach ($p in $pids) {
        Write-Host "Attempting to kill PID $p (owner of :8000)"
        try {
            taskkill /PID $p /F | Write-Host
        } catch {
            Write-Host "taskkill failed for PID $p: $_"
        }
    }
} else {
    Write-Host 'No PIDs found for :8000'
}
Start-Sleep -s 1
Write-Host 'Starting uvicorn main:app on 127.0.0.1:8000 (background)'
$env:JWT_SECRET_KEY='devsecret'
$env:DATA_DIR='C:\Users\gebruiker\Desktop\mijn_api'
$env:ALLOW_DEBUG='1'
Start-Process -NoNewWindow -FilePath 'C:\Users\gebruiker\Desktop\mijn_api\venv2\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000'
Start-Sleep -s 1
Write-Host '=== netstat after start ==='
netstat -ano | Select-String ':8000' | ForEach-Object { Write-Host $_ }
Pop-Location
