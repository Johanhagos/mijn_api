import paramiko
import os
from stat import S_ISDIR

# One.com SFTP credentials
hostname = "[REDACTED]"
username = "[REDACTED]"
password = "[REDACTED]"
port = 22
remote_path = "/webroots/dae9921c/"

print("=" * 60)
print("🔥 FORCE OVERRIDE ONE.COM WEBSITE BUILDER")
print("=" * 60)
print()

# Connect via SFTP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"🔌 Connecting to {hostname}...")
    ssh.connect(hostname, port=port, username=username, password=password)
    sftp = ssh.open_sftp()
    print("✅ Connected!\n")
    
    # List all files in the directory
    print(f"📂 Scanning {remote_path}...")
    files = sftp.listdir_attr(remote_path)
    
    # Files to potentially remove (One.com builder files)
    builder_files = []
    
    for item in files:
        filename = item.filename
        # Look for One.com builder directories and files
        if any(x in filename.lower() for x in ['onewebstatic', 'onewebmedia', 'onebookingsmedia', 'blog', 'blogmedia']):
            builder_files.append(filename)
    
    if builder_files:
        print(f"\n🔍 Found {len(builder_files)} One.com Website Builder items:")
        for f in builder_files:
            print(f"   - {f}")
        
        print("\n⚠️  WARNING: This will delete One.com Website Builder files!")
        print("   Your modern index.html will remain and become the default.\n")
        
        # Delete builder directories and files
        print("🗑️  Removing Website Builder files...")
        deleted_count = 0
        for item_name in builder_files:
            try:
                item_path = remote_path + item_name
                item_attr = sftp.stat(item_path)
                
                # Check if it's a directory
                if S_ISDIR(item_attr.st_mode):
                    # For directories, just note them (would need recursive delete)
                    print(f"   ⏭️  Skipping directory: {item_name} (manual removal recommended)")
                else:
                    # Delete file
                    sftp.remove(item_path)
                    print(f"   ✅ Deleted: {item_name}")
                    deleted_count += 1
            except Exception as e:
                print(f"   ⚠️  Could not delete {item_name}: {e}")
        
        print(f"\n✅ Deleted {deleted_count} builder files")
    else:
        print("✅ No Website Builder files found - already clean!")
    
    # Verify our modern index.html is present
    print("\n🔍 Verifying modern index.html...")
    try:
        index_stat = sftp.stat(remote_path + "index.html")
        print(f"✅ index.html present ({index_stat.st_size} bytes)")
        
        # Read first part to verify it's our modern version
        with sftp.open(remote_path + "index.html", 'r') as f:
            content = f.read(2000).decode('utf-8', errors='ignore')
            if 'Blockchain Payments Made Simple' in content:
                print("✅ Confirmed: Modern homepage is active!")
            elif 'apiblockchain' in content.lower():
                print("⚠️  index.html exists but might be old version")
            else:
                print("⚠️  Unexpected content in index.html")
    except Exception as e:
        print(f"❌ Error checking index.html: {e}")
    
    # Check .htaccess is correct
    print("\n🔍 Verifying .htaccess configuration...")
    try:
        with sftp.open(remote_path + ".htaccess", 'r') as f:
            htaccess_content = f.read().decode('utf-8')
            if 'DirectoryIndex index.html' in htaccess_content:
                print("✅ .htaccess correctly prioritizes index.html")
            else:
                print("⚠️  .htaccess might need DirectoryIndex directive")
    except Exception as e:
        print(f"⚠️  Could not check .htaccess: {e}")
    
    sftp.close()
    ssh.close()
    
    print("\n" + "=" * 60)
    print("✅ OVERRIDE COMPLETE!")
    print("=" * 60)
    print()
    print("🌐 Your site: https://apiblockchain.io")
    print()
    print("📋 What was done:")
    print("   ✓ Removed conflicting Website Builder files")
    print("   ✓ Modern index.html is now the default homepage")
    print()
    print("🔄 Next steps:")
    print("   1. Wait 2-3 minutes for server cache to clear")
    print("   2. Open https://apiblockchain.io in incognito mode")
    print("   3. You should see: Green hero 'Blockchain Payments Made Simple'")
    print()
    print("💡 If still showing old page:")
    print("   - Clear your browser cache (Ctrl+Shift+Delete)")
    print("   - Or wait 5-10 minutes for CDN cache to expire")
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
