#!/usr/bin/env python3
"""
List all PHP and config files to understand the setup
"""
import paramiko

host = "ssh.cruerobt5.service.one"
username = "cruerobt5_ssh"
password = "Johanahagos1992&"
port = 22

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    
    sftp = ssh.open_sftp()
    
    print("Files in webroots/dae9921c/:\n")
    files = []
    for item in sftp.listdir_attr("webroots/dae9921c/"):
        if not item.filename.startswith('.') and item.filename.endswith(('.html', '.php', '.json')):
            files.append(item.filename)
    
    for f in sorted(files):
        print(f"  {f}")
    
    print("\n\nChecking sendmail.php...")
    with sftp.open("webroots/dae9921c/sendmail.php", 'r') as f:
        content = f.read().decode('utf-8', errors='ignore')
        print(content[:500])
    
    sftp.close()
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
