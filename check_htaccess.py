#!/usr/bin/env python3
"""
Check .htaccess and other config files
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
    
    # Check for .htaccess
    print("Checking for .htaccess files...")
    try:
        with sftp.open("webroots/dae9921c/.htaccess", 'r') as f:
            content = f.read().decode('utf-8', errors='ignore')
            print("\n.htaccess content:")
            print(content[:1000])
    except:
        print("No .htaccess found")
    
    # List all files in root
    print("\n\nAll files in webroots/dae9921c/:")
    for item in sftp.listdir_attr("webroots/dae9921c/"):
        if item.filename.startswith('.'):
            print(f"  {item.filename} (size: {item.st_size})")
    
    sftp.close()
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
