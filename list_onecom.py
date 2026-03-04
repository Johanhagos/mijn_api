#!/usr/bin/env python3
import paramiko
import os

host = "[REDACTED]"
username = "[REDACTED]"
password = "[REDACTED]"
port = 22
remote_root = "webroots/dae9921c"

def fmt_attr(attr):
    return f"{attr.filename}\t{attr.st_size} bytes"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {host}...")
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

    # Check specific files
    targets = [f"{remote_root}/contact.html", f"{remote_root}/contact/index.html"]
    for t in targets:
        try:
            st = sftp.stat(t)
            print(f"FOUND: {t} ({st.st_size} bytes)")
        except IOError:
            print(f"MISSING: {t}")

    sftp.close()
    ssh.close()
except Exception as exc:
    print('Error:', exc)
