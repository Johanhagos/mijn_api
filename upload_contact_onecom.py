#!/usr/bin/env python3
"""
Upload contact.html to One.com via SFTP
"""
import os
import sys
import paramiko

# Read connection details from environment variables to avoid storing secrets in the repo.
# Required: ONE_SFTP_HOST, ONE_SFTP_USER, ONE_SFTP_PASSWORD
# Optional: ONE_SFTP_PORT (default 22)

host = os.environ.get("ONE_SFTP_HOST")
username = os.environ.get("ONE_SFTP_USER")
password = os.environ.get("ONE_SFTP_PASSWORD")
port = int(os.environ.get("ONE_SFTP_PORT", "22"))

# Files to upload
# Disabled by default: keep empty to avoid accidental uploads.
files = []

if not (host and username and password):
    print("Missing SFTP credentials. Set ONE_SFTP_HOST, ONE_SFTP_USER, and ONE_SFTP_PASSWORD environment variables.")
    sys.exit(1)

print("=" * 60)
print("Uploading files to One.com via SFTP")
print("=" * 60)
print(f"Host: {host}:{port}")
print(f"Username: {username}")
print()

if not files:
    print("No files configured to upload — upload is disabled by default.")
    sys.exit(0)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    print("Connecting to server...")
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    print("✓ Connected!")

    sftp = ssh.open_sftp()
    print("✓ SFTP channel opened!")

    for local_file, remote_path in files:
        filename = os.path.basename(local_file)
        print(f"\nUploading {filename}...")

        if not os.path.exists(local_file):
            print(f"✗ Local file not found: {local_file}")
            continue

        local_size = os.path.getsize(local_file)
        print(f"✓ Local file found ({local_size} bytes)")

        remote_dir = os.path.dirname(remote_path)
        try:
            parts = remote_dir.split('/')
            path = ''
            for part in parts:
                if not part:
                    continue
                path = f"{path}/{part}" if path else part
                try:
                    sftp.stat(path)
                except IOError:
                    try:
                        sftp.mkdir(path)
                        print(f"✓ Created remote directory: {path}")
                    except Exception:
                        pass
        except Exception:
            pass

        sftp.put(local_file, remote_path)

        try:
            remote_size = sftp.stat(remote_path).st_size
            if remote_size == local_size:
                print(f"✓ {filename} uploaded successfully to {remote_path}")
            else:
                print(f"⚠ Warning: File sizes don't match (local: {local_size}, remote: {remote_size})")
        except Exception as e:
            print(f"✗ Could not verify {filename}: {e}")

    sftp.close()
    ssh.close()

    print("\n" + "=" * 60)
    print("✓ UPLOAD COMPLETE!")
    print("=" * 60)

except paramiko.AuthenticationException:
    print("✗ Authentication failed. Check username and password.")
    sys.exit(1)
except paramiko.SSHException as e:
    print(f"✗ SSH error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
finally:
    try:
        if 'sftp' in globals() and sftp:
            sftp.close()
        if 'ssh' in globals() and ssh:
            ssh.close()
    except Exception:
        pass
