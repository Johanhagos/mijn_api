#!/usr/bin/env python3
"""
List directory structure on One.com to find correct path
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
    
    print("Current directory:", sftp.getcwd())
    print("\nListing root directory:")
    for item in sftp.listdir():
        print(f"  {item}")
    
    print("\nTrying to list webroots...")
    try:
        for item in sftp.listdir("webroots"):
            print(f"  {item}")
    except Exception as e:
        print(f"  Error listing webroots: {e}")
    
    print("\nTrying to list webroots/dae9921c...")
    try:
        for item in sftp.listdir("webroots/dae9921c"):
            print(f"  {item}")
    except Exception as e:
        print(f"  Error: {e}")
    
    sftp.close()
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
