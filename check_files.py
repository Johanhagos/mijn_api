#!/usr/bin/env python3
"""
List all PHP and config files to understand the setup
"""
import paramiko
import os

# One.com SFTP credentials from environment
host = os.environ.get("ONE_SFTP_HOST")
username = os.environ.get("ONE_SFTP_USER")
password = os.environ.get("ONE_SFTP_PASSWORD")
port = int(os.environ.get("ONE_SFTP_PORT", "22"))

if not (host and username and password):
    print("Missing SFTP credentials. Set ONE_SFTP_HOST, ONE_SFTP_USER, and ONE_SFTP_PASSWORD environment variables.")
    raise SystemExit(1)

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
