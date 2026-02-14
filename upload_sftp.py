#!/usr/bin/env python3
"""
Upload index.html to One.com via SFTP
"""
import paramiko
import os

# Connection details
host = "ssh.cruerobt5.service.one"
username = "cruerobt5_ssh"
password = "Johanahagos1992&"
port = 22

# Local file to upload
local_file = r"c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload\index.html"
remote_path = "webroots/dae9921c/index.html"

print("=" * 60)
print("Uploading to One.com via SFTP")
print("=" * 60)
print(f"Host: {host}:{port}")
print(f"Username: {username}")
print(f"Local file: {local_file}")
print(f"Remote path: {remote_path}")
print()

try:
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Connect
    print("Connecting to server...")
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    print("✓ Connected!")
    
    # Open SFTP channel
    sftp = ssh.open_sftp()
    print("✓ SFTP channel opened!")
    
    # Check if file exists locally
    if not os.path.exists(local_file):
        print(f"✗ Local file not found: {local_file}")
        sftp.close()
        ssh.close()
        exit(1)
    
    print(f"✓ Local file found ({os.path.getsize(local_file)} bytes)")
    
    # Upload file
    print(f"Uploading {os.path.basename(local_file)}...")
    sftp.put(local_file, remote_path)
    print(f"✓ File uploaded to {remote_path}")
    
    # Verify upload
    try:
        stat = sftp.stat(remote_path)
        print(f"✓ Upload verified! Remote file size: {stat.st_size} bytes")
    except:
        print("! Could not verify upload (file may be there anyway)")
    
    # Close connection
    sftp.close()
    ssh.close()
    
    print()
    print("=" * 60)
    print("✓ UPLOAD SUCCESSFUL!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Hard refresh your browser: Ctrl+Shift+R")
    print("2. The modern homepage with title and AI should now be visible!")
    print()
    
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)
