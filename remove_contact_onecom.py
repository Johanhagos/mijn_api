#!/usr/bin/env python3
"""
Remove contact files from One.com via SFTP.
Run this only if you want to delete the remote contact copies.
"""
import os
import sys
import paramiko

# Use environment variables for credentials to avoid committing secrets.
# Required env vars: ONE_SFTP_HOST, ONE_SFTP_USER, ONE_SFTP_PASSWORD
# Optional: ONE_SFTP_PORT (defaults to 22), ONE_SFTP_REMOTE_ROOT

host = os.environ.get("ONE_SFTP_HOST")
username = os.environ.get("ONE_SFTP_USER")
password = os.environ.get("ONE_SFTP_PASSWORD")
port = int(os.environ.get("ONE_SFTP_PORT", "22"))
remote_root = os.environ.get("ONE_SFTP_REMOTE_ROOT", "webroots/dae9921c")

if not (host and username and password):
    print("Missing SFTP credentials. Set ONE_SFTP_HOST, ONE_SFTP_USER, and ONE_SFTP_PASSWORD environment variables.")
    sys.exit(1)

targets = [f"{remote_root}/contact.html", f"{remote_root}/contact/index.html"]

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host}:{port} as {username}...")
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
