#!/usr/bin/env python3
"""
Check what files are currently on one.com
"""
import paramiko

HOST = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
PORT = 22
REMOTE_PATH = "/webroots/dae9921c/"

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
