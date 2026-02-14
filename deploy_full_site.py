#!/usr/bin/env python3
"""
Full Site Deployment - Deploys entire webshop and removes old pages
"""
import paramiko
import os
import sys
from pathlib import Path

# Connection details
HOST = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
PORT = 22
REMOTE_PATH = "/webroots/dae9921c/"
LOCAL_PATH = "c:/Users/gebruiker/Desktop/mijn_api/webshop_for_upload"

print("=" * 60)
print("🚀 FULL SITE DEPLOYMENT - APIBlockchain Webshop")
print("=" * 60)
print()

try:
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"🔌 Connecting to {HOST}...")
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    print("✅ Connected successfully!")
    print()
    
    # Open SFTP session
    sftp = ssh.open_sftp()
    
    # Files to DELETE from server (old pages)
    files_to_delete = [
        "services.html",
        "quotation.html",
        "booking.html",
    ]
    
    print("🗑️  Removing old pages...")
    for filename in files_to_delete:
        remote_file = REMOTE_PATH + filename
        try:
            sftp.remove(remote_file)
            print(f"   ✓ Deleted: {filename}")
        except FileNotFoundError:
            print(f"   - Not found: {filename}")
        except Exception as e:
            print(f"   ⚠️  Error deleting {filename}: {e}")
    print()
    
    # Files to UPLOAD
    files_to_upload = [
        "index.html",
        "checkout.html",
        "about.html",
        "contact.html",
        "thank-you.html",
        ".htaccess",
    ]
    
    print(f"📤 Uploading files from: {LOCAL_PATH}")
    print(f"📍 To: {REMOTE_PATH}")
    print()
    
    for filename in files_to_upload:
        local_file = os.path.join(LOCAL_PATH, filename)
        remote_file = REMOTE_PATH + filename
        
        if os.path.exists(local_file):
            try:
                print(f"   Uploading: {filename}...", end=" ")
                sftp.put(local_file, remote_file)
                # Set proper permissions
                sftp.chmod(remote_file, 0o644)
                print("✅")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print(f"   ⚠️  File not found locally: {filename}")
    
    print()
    print("🔧 Setting proper permissions on server...")
    try:
        sftp.chmod(REMOTE_PATH + "index.html", 0o644)
        sftp.chmod(REMOTE_PATH + ".htaccess", 0o644)
        print("   ✓ Permissions set")
    except Exception as e:
        print(f"   ⚠️  Permission error: {e}")
    
    # Close connection
    sftp.close()
    ssh.close()
    
    print()
    print("=" * 60)
    print("✅ FULL DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print()
    print("🌐 Your website is live at:")
    print("   👉 https://apiblockchain.io")
    print()
    print("📋 What was deployed:")
    print("   ✓ Modern homepage (green gradient, features, pricing)")
    print("   ✓ Checkout page (multi-payment)")
    print("   ✓ About & Contact pages")
    print("   ✓ Navigation updated (removed Blog/quotation/booking)")
    print()
    print("🔄 To see changes:")
    print("   1. Press Ctrl+Shift+Delete → Clear cache")
    print("   2. Or open Incognito: Ctrl+Shift+N")
    print("   3. Look for '✅ MODERN V2 LOADED' badge on homepage")
    print()
    print("🎯 Expected to see:")
    print("   • Green hero: 'Blockchain Payments Made Simple'")
    print("   • 6 feature cards (Lightning, Secure, Smart Invoicing, etc)")
    print("   • Dashboard preview section")
    print("   • 3 pricing cards (Starter, Professional, Enterprise)")
    print("   • AI chat button (💬) in bottom-right")
    print()
    
except Exception as e:
    print(f"❌ DEPLOYMENT FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
