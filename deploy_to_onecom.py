#!/usr/bin/env python3
"""
APIBlockchain Webshop Deployment Script
Uploads webshop files to one.com via SFTP
"""
import paramiko
import os
import sys
from pathlib import Path

# Connection details
HOST = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
PORT = 22
REMOTE_PATH = "/webroots/dae9921c/"
LOCAL_PATH = "c:/Users/gebruiker/Desktop/mijn_api/webshop_for_upload"

print("=" * 50)
print("APIBlockchain Webshop Deployment")
print("Target: one.com")
print("=" * 50)
print()

try:
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {HOST}...")
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    print("✓ Connected successfully!")
    print()
    
    # Open SFTP session
    sftp = ssh.open_sftp()
    
    # Files to upload
    files_to_upload = [
        "index.html",
        "checkout.html",
        ".htaccess",
    ]
    
    print(f"Uploading files from: {LOCAL_PATH}")
    print(f"To: {REMOTE_PATH}")
    print()
    
    for filename in files_to_upload:
        local_file = os.path.join(LOCAL_PATH, filename)
        remote_file = REMOTE_PATH + filename
        
        if os.path.exists(local_file):
            try:
                print(f"Uploading: {filename}...", end=" ")
                sftp.put(local_file, remote_file)
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
        else:
            print(f"File not found: {local_file}")
    
    # Close connection
    sftp.close()
    ssh.close()
    
    print()
    print("✓ Deployment complete!")
    print()
    print("Your website should be live at:")
    print("  https://apiblockchain.io")
    print()
    print("Next steps:")
    print("  1. Clear your browser cache (Ctrl+Shift+Delete)")
    print("  2. Visit https://apiblockchain.io in incognito mode")
    print("  3. Check for green theme, dashboard, and AI chat button")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
