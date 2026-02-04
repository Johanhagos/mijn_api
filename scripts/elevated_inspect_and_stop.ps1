# Elevated inspection and stop script for port 8000
# Requires Administrator approval (UAC).
Push-Location 'C:\Users\gebruiker\Desktop\mijn_api'
$log = 'c:\Users\gebruiker\Desktop\mijn_api\scripts\port8000_owner.txt'
"=== Running netstat -ab -o (requires admin) ===" | Out-File -FilePath $log -Encoding utf8
try {
    netstat -ab -o 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
} catch {
    "netstat -ab -o failed: $_" | Out-File -FilePath $log -Append -Encoding utf8
}

# Parse PIDs
$pids = netstat -ano | Select-String ':8000' | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^[0-9]+$' } | Select-Object -Unique
"PIDs: $($pids -join ',')" | Out-File -FilePath $log -Append -Encoding utf8

if ($pids) {
    foreach ($p in $pids) {
        "=== Inspecting process $p ===" | Out-File -FilePath $log -Append -Encoding utf8
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$p" | Select-Object ProcessId,Name,CommandLine,ExecutablePath
            if ($proc) {
                $proc | Out-File -FilePath $log -Append -Encoding utf8
            } else {
                "Get-CimInstance returned no data for PID $p" | Out-File -FilePath $log -Append -Encoding utf8
            }
        } catch {
            "Get-CimInstance failed for PID $p: $_" | Out-File -FilePath $log -Append -Encoding utf8
        }

        # Attempt to stop
        try {
            Stop-Process -Id $p -Force -ErrorAction Stop
            "Stop-Process succeeded for PID $p" | Out-File -FilePath $log -Append -Encoding utf8
        } catch {
            "Stop-Process failed for PID $p: $_" | Out-File -FilePath $log -Append -Encoding utf8
            try {
                taskkill /PID $p /F 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
            } catch {
                "taskkill failed for PID $p: $_" | Out-File -FilePath $log -Append -Encoding utf8
            }
        }
    }
} else {
    "No PIDs found for :8000" | Out-File -FilePath $log -Append -Encoding utf8
}

Start-Sleep -s 1
"=== netstat after attempting kills ===" | Out-File -FilePath $log -Append -Encoding utf8
netstat -ano | Select-String ':8000' | Out-File -FilePath $log -Append -Encoding utf8

# Start uvicorn
"Starting uvicorn main:app on 127.0.0.1:8000 (background)" | Out-File -FilePath $log -Append -Encoding utf8
$env:JWT_SECRET_KEY='devsecret'
$env:DATA_DIR='C:\Users\gebruiker\Desktop\mijn_api'
$env:ALLOW_DEBUG='1'
Start-Process -NoNewWindow -FilePath 'C:\Users\gebruiker\Desktop\mijn_api\venv2\Scripts\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000'
Start-Sleep -s 2
"=== netstat after starting uvicorn ===" | Out-File -FilePath $log -Append -Encoding utf8
netstat -ano | Select-String ':8000' | Out-File -FilePath $log -Append -Encoding utf8

"Log saved to: $log" | Out-File -FilePath $log -Append -Encoding utf8
Pop-Location
