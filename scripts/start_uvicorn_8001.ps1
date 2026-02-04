$matches = netstat -ano | Select-String ':8001' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Unique
if ($matches) { foreach ($p in $matches) { Write-Host "Killing process $p using port 8001"; taskkill /PID $p /F } } else { Write-Host "No process found on port 8001" }
Start-Sleep -s 1
$env:JWT_SECRET_KEY='devsecret'
$env:DATA_DIR='C:\Users\gebruiker\Desktop\mijn_api'
$env:ALLOW_DEBUG='1'
Start-Process -NoNewWindow -FilePath 'C:\Users\gebruiker\Desktop\mijn_api\venv2\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8001' -WorkingDirectory 'C:\Users\gebruiker\Desktop\mijn_api'
Write-Host 'uvicorn started on 8001 (background)'
