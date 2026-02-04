Push-Location 'C:\Users\gebruiker\Desktop\mijn_api'
$env:JWT_SECRET_KEY='devsecret'
$env:DATA_DIR='C:\Users\gebruiker\Desktop\mijn_api'
$env:ALLOW_DEBUG='1'
$p = Start-Process -FilePath 'C:\Users\gebruiker\Desktop\mijn_api\venv2\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8002' -NoNewWindow -PassThru
Start-Sleep -s 1
Write-Output "Started PID: $($p.Id)"
netstat -ano | Select-String ':8002' | ForEach-Object { Write-Output $_ }
Pop-Location
