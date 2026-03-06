#!/usr/bin/env python3
"""
Download current index.html from server to inspect it
"""
import paramiko
import os

# One.com SFTP credentials from environment
HOST = os.environ.get("ONE_SFTP_HOST")
USERNAME = os.environ.get("ONE_SFTP_USER")
PASSWORD = os.environ.get("ONE_SFTP_PASSWORD")
PORT = int(os.environ.get("ONE_SFTP_PORT", "22"))
REMOTE_PATH = os.environ.get("ONE_SFTP_REMOTE_ROOT", "/webroots/dae9921c/")

if not (HOST and USERNAME and PASSWORD):
    print("Missing SFTP credentials. Set ONE_SFTP_HOST, ONE_SFTP_USER, and ONE_SFTP_PASSWORD environment variables.")
    raise SystemExit(1)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print("Connecting and downloading server index.html...")
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    
    sftp = ssh.open_sftp()
    sftp.get(REMOTE_PATH + "index.html", "server_index.html")
    
    print("✅ Downloaded to: server_index.html")
    print()
    
    # Read first 2000 chars
    with open("server_index.html", 'r', encoding='utf-8') as f:
        content = f.read(2000)
        print("First 2000 characters of server file:")
        print("=" * 60)
        print(content)
        print("=" * 60)
    
    sftp.close()
    ssh.close()
    
except Exception as e:
    print(f"Error: {e}")
