$matches = netstat -ano | Select-String ':3001' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Unique
if ($matches) { foreach ($p in $matches) { Write-Host "Killing process $p using port 3001"; taskkill /PID $p /F } } else { Write-Host "No process found on port 3001" }
Start-Sleep -s 1
Set-Location 'C:\Users\gebruiker\Desktop\mijn_api\merchant-dashboard'
$env:PORT='3001'
Start-Process -NoNewWindow -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory 'C:\Users\gebruiker\Desktop\mijn_api\merchant-dashboard'
Write-Host 'Next dev started (background)'
