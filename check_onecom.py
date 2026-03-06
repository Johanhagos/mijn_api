#!/usr/bin/env python3
"""
Check what files are currently on one.com
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
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    
    sftp = ssh.open_sftp()
    
    print("Files on one.com:")
    print()
    
    for item in sftp.listdir_attr(REMOTE_PATH):
        if item.filename.startswith('.'):
            continue
        size = f"{item.st_size:,} bytes" if item.st_size else "DIR"
        print(f"  {item.filename:30} {size}")
    
    # Download current index.html to see what's live
    print()
    print("Downloading current index.html from one.com...")
    sftp.get(REMOTE_PATH + "index.html", "current_index.html")
    print("✓ Saved as: current_index.html")
    
    sftp.close()
    ssh.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
