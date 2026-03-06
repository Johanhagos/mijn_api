#!/usr/bin/env python3
import paramiko
import os

import os

# Use environment variables for credentials
host = os.environ.get("ONE_SFTP_HOST")
username = os.environ.get("ONE_SFTP_USER")
password = os.environ.get("ONE_SFTP_PASSWORD")
port = int(os.environ.get("ONE_SFTP_PORT", "22"))
remote_root = os.environ.get("ONE_SFTP_REMOTE_ROOT", "webroots/dae9921c")

def fmt_attr(attr):
    return f"{attr.filename}\t{attr.st_size} bytes"

if not (host and username and password):
    print("Missing SFTP credentials. Set ONE_SFTP_HOST, ONE_SFTP_USER, and ONE_SFTP_PASSWORD environment variables.")
    raise SystemExit(1)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host}:{port} as {username}...")
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    sftp = ssh.open_sftp()
    print("Connected via SFTP. Listing:")
    try:
        entries = sftp.listdir_attr(remote_root)
    except IOError as e:
        print(f"Could not list {remote_root}: {e}")
        entries = []

    for e in entries:
        print(fmt_attr(e))

    # Note: contact files are no longer deployed to One.com by default.
    # Remove or check them manually using `remove_contact_onecom.py` if needed.

    sftp.close()
    ssh.close()
except Exception as exc:
    print('Error:', exc)
