#!/usr/bin/env python3
"""
FORCE UPLOAD with verification
"""
import paramiko
import os
import sys

HOST = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
PORT = 22
REMOTE_PATH = "/webroots/dae9921c/"
LOCAL_PATH = "c:/Users/gebruiker/Desktop/mijn_api/webshop_for_upload"

print("=" * 70)
print("🚀 FORCE UPLOAD - Modern Homepage to One.com")
print("=" * 70)
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"🔌 Connecting to {HOST}...")
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    print("✅ Connected!")
    print()
    
    sftp = ssh.open_sftp()
    
    local_file = os.path.join(LOCAL_PATH, "index.html")
    remote_file = REMOTE_PATH + "index.html"
    backup_file = REMOTE_PATH + "index.html.backup"
    
    # Check local file
    print("📄 Checking local file...")
    with open(local_file, 'r', encoding='utf-8') as f:
        local_content = f.read()
        print(f"   Size: {len(local_content)} bytes")
        if 'Blockchain Payments Made Simple' in local_content:
            print("   ✅ Modern content confirmed")
        else:
            print("   ❌ ERROR: Local file doesn't have modern content!")
            sys.exit(1)
    
    print()
    print("💾 Creating backup of current server file...")
    try:
        # Backup current file
        sftp.rename(remote_file, backup_file)
        print("   ✅ Backup created: index.html.backup")
    except:
        print("   ⚠️  No existing file to backup (or backup failed)")
    
    print()
    print("📤 Uploading NEW index.html...")
    sftp.put(local_file, remote_file)
    print("   ✅ Upload complete")
    
    print()
    print("🔧 Setting permissions...")
    sftp.chmod(remote_file, 0o644)
    print("   ✅ Permissions set (644)")
    
    print()
    print("✅ Verifying upload...")
    with sftp.open(remote_file, 'r') as f:
        remote_content = f.read(5000).decode('utf-8')
        
        checks = {
            'Blockchain Payments Made Simple': False,
            'MODERN V2 LOADED': False,
            'dashboard-section': False,
            '#features': False
        }
        
        for check_text in checks.keys():
            if check_text in remote_content:
                checks[check_text] = True
                print(f"   ✅ Found: '{check_text}'")
            else:
                print(f"   ❌ Missing: '{check_text}'")
        
        if all(checks.values()):
            print()
            print("=" * 70)
            print("🎉 SUCCESS! Modern homepage is NOW LIVE on server!")
            print("=" * 70)
        else:
            print()
            print("⚠️  WARNING: Upload succeeded but some content checks failed")
    
    # Get file stats
    attrs = sftp.stat(remote_file)
    print()
    print(f"📊 Server file info:")
    print(f"   Size: {attrs.st_size} bytes")
    print(f"   Permissions: {oct(attrs.st_mode)}")
    
    sftp.close()
    ssh.close()
    
    print()
    print("=" * 70)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 70)
    print()
    print("🌐 Visit: https://apiblockchain.io")
    print("🔄 Hard refresh: Ctrl+Shift+R")
    print("🕶️  Incognito: Ctrl+Shift+N")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
