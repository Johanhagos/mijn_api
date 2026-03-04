#!/usr/bin/env python3
"""
Upload contact.html to One.com via SFTP
"""
import paramiko
import os

# Connection details
host = "[REDACTED]"
username = "[REDACTED]"
password = "[REDACTED]"
port = 22

# Files to upload
files = [
    (r"c:\Users\gebruiker\Desktop\mijn_api\webshop\contact.html", "webroots/dae9921c/contact.html"),
    (r"c:\Users\gebruiker\Desktop\mijn_api\webshop\contact.html", "webroots/dae9921c/contact/index.html"),
]

print("=" * 60)
print("Uploading files to One.com via SFTP")
print("=" * 60)
print(f"Host: {host}:{port}")
print(f"Username: {username}")
print()

try:
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Connect
    print("Connecting to server...")
    ssh.connect(host, port=port, username=username, password=password, timeout=10)
    print("✓ Connected!")
    
    # Open SFTP channel
    sftp = ssh.open_sftp()
    print("✓ SFTP channel opened!")
    
    # Upload files
    for local_file, remote_path in files:
        filename = os.path.basename(local_file)
        print(f"\nUploading {filename}...")
        
        # Check if file exists locally
        if not os.path.exists(local_file):
            print(f"✗ Local file not found: {local_file}")
            continue
            
        local_size = os.path.getsize(local_file)
        print(f"✓ Local file found ({local_size} bytes)")
        
        # Ensure remote directory exists (mkdir -p)
        remote_dir = os.path.dirname(remote_path)
        try:
            # walk and create directories if needed
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

        # Upload file
        sftp.put(local_file, remote_path)
        
        # Verify upload
        try:
            remote_size = sftp.stat(remote_path).st_size
            if remote_size == local_size:
                print(f"✓ {filename} uploaded successfully to {remote_path}")
            else:
                print(f"⚠ Warning: File sizes don't match (local: {local_size}, remote: {remote_size})")
        except Exception as e:
            print(f"✗ Could not verify {filename}: {e}")
    
    # Close connections
    sftp.close()
    ssh.close()
    
    print("\n" + "=" * 60)
    print("✓ UPLOAD COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Hard refresh your browser: Ctrl+Shift+R")
    print("2. Visit: https://apiblockchain.io/contact")
    print("3. The updated contact page should now be visible!")
    
except paramiko.AuthenticationException:
    print("✗ Authentication failed. Check username and password.")
except paramiko.SSHException as e:
    print(f"✗ SSH error: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    try:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
    except:
        pass
