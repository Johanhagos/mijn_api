#!/usr/bin/env python3
"""
Verify what files are on One.com server
"""
import paramiko
import sys

HOST = "[REDACTED]"
USERNAME = "[REDACTED]"
PASSWORD = "[REDACTED]"
PORT = 22
REMOTE_PATH = "/webroots/dae9921c/"

print("=" * 60)
print("🔍 CHECKING ONE.COM SERVER FILES")
print("=" * 60)
print()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"🔌 Connecting to {HOST}...")
    ssh.connect(HOST, port=PORT, username=USERNAME, password=PASSWORD, timeout=30)
    print("✅ Connected!")
    print()
    
    sftp = ssh.open_sftp()
    
    print(f"📂 Files in {REMOTE_PATH}:")
    print()
    
    files = sftp.listdir(REMOTE_PATH)
    html_files = [f for f in files if f.endswith('.html') or f == '.htaccess']
    html_files.sort()
    
    for filename in html_files:
        try:
            attrs = sftp.stat(REMOTE_PATH + filename)
            size_kb = attrs.st_size / 1024
            print(f"   📄 {filename:<25} ({size_kb:.1f} KB)")
        except:
            print(f"   📄 {filename}")
    
    print()
    print(f"📊 Total HTML files: {len([f for f in html_files if f.endswith('.html')])}")
    
    # Check index.html content snippet
    print()
    print("=" * 60)
    print("🔎 Checking index.html content...")
    print("=" * 60)
    
    try:
        with sftp.open(REMOTE_PATH + 'index.html', 'r') as f:
            content = f.read(5000).decode('utf-8')
            
            if 'Blockchain Payments Made Simple' in content:
                print("✅ MODERN HOMEPAGE DETECTED!")
                print("   Found: 'Blockchain Payments Made Simple'")
            else:
                print("⚠️  OLD HOMEPAGE DETECTED")
                
            if 'MODERN V2 LOADED' in content:
                print("✅ Version badge present")
            else:
                print("⚠️  Version badge missing")
                
            if 'dashboard-section' in content:
                print("✅ Dashboard section present")
            else:
                print("⚠️  Dashboard section missing")
                
            if 'Features | Pricing | About | Contact' in content or 'href="#features"' in content:
                print("✅ Modern navigation detected")
            else:
                print("⚠️  Old navigation might be present")
    except Exception as e:
        print(f"❌ Could not read index.html: {e}")
    
    sftp.close()
    ssh.close()
    
    print()
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
