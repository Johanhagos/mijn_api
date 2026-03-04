#!/usr/bin/env python3
"""
Remove contact files from One.com via SFTP.
Run this only if you want to delete the remote contact copies.
"""
import paramiko

host = "[REDACTED]"
username = "[REDACTED]"
password = "[REDACTED]"
port = 22
remote_root = "webroots/dae9921c"

targets = [f"{remote_root}/contact.html", f"{remote_root}/contact/index.html"]

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host}...")
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    sftp = ssh.open_sftp()
    print("Connected via SFTP. Removing targets:")
    for t in targets:
        try:
            sftp.remove(t)
            print(f"Removed: {t}")
        except IOError:
            print(f"Not found or could not remove: {t}")
    sftp.close()
    ssh.close()
except Exception as exc:
    print('Error:', exc)
