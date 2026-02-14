#!/usr/bin/env python3
"""
Verify the uploaded file and check its content
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
    
    # Check the file
    remote_file = "webroots/dae9921c/index.html"
    
    print(f"Checking {remote_file}...")
    stat = sftp.stat(remote_file)
    print(f"File size: {stat.st_size} bytes")
    print(f"Last modified: {stat.st_mtime}")
    
    print("\nFirst 500 characters of file:")
    with sftp.open(remote_file, 'r') as f:
        content = f.read(500)
        print(content.decode('utf-8', errors='ignore'))
    
    print("\n...")
    print("\nChecking for 'Blockchain Payments Made Simple'...")
    with sftp.open(remote_file, 'r') as f:
        full_content = f.read().decode('utf-8', errors='ignore')
        if "Blockchain Payments Made Simple" in full_content:
            print("✓ Modern content is on the server!")
        else:
            print("✗ Old content detected - modern version not uploaded")
    
    sftp.close()
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
