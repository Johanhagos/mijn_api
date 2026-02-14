#!/usr/bin/env python3
"""
List directory structure on One.com to find correct path
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
