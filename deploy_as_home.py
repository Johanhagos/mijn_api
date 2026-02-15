import paramiko
import os

# One.com SFTP connection details
HOSTNAME = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
REMOTE_PATH = "/webroots/dae9921c/"

print("🚀 DEPLOYING AS home.html TO BYPASS WEBSITE BUILDER")
print("=" * 60)

# Connect via SFTP
transport = paramiko.Transport((HOSTNAME, 22))
transport.connect(username=USERNAME, password=PASSWORD)
sftp = paramiko.SFTPClient.from_transport(transport)

print(f"✅ Connected to {HOSTNAME}")

# Upload index.html as BOTH index.html AND home.html
local_file = "webshop_for_upload/index.html"
files_to_upload = [
    ("index.html", "webshop_for_upload/index.html"),
    ("home.html", "webshop_for_upload/index.html"),  # Same content, different name
]

for remote_name, local_path in files_to_upload:
    remote_file = REMOTE_PATH + remote_name
    print(f"📤 Uploading {local_path} → {remote_name}...")
    sftp.put(local_path, remote_file)
    sftp.chmod(remote_file, 0o644)
    print(f"   ✅ Uploaded {remote_name}")

# Create updated .htaccess with multiple fallbacks
htaccess_content = """# Force custom homepage (multiple strategies)
DirectoryIndex home.html index.html default.html

# Explicit redirect to home.html
RewriteEngine On
RewriteCond %{REQUEST_URI} ^/$
RewriteRule ^$ /home.html [L]

# Disable Website Builder routing
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /home.html [L]
</IfModule>

# Cache control for HTML
<FilesMatch "\\.(html|htm)$">
Header set Cache-Control "no-cache, no-store, must-revalidate, max-age=0"
Header set Pragma "no-cache"
Header set Expires "0"
</FilesMatch>

# Force HTTPS for apiblockchain.io
RewriteCond %{HTTP_HOST} ^apiblockchain\\.io [NC]
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
"""

# Upload new .htaccess
htaccess_path = REMOTE_PATH + ".htaccess"
print(f"📤 Uploading new .htaccess with home.html priority...")
sftp.file(htaccess_path, 'w').write(htaccess_content)
sftp.chmod(htaccess_path, 0o644)
print("   ✅ .htaccess updated")

print("\n" + "=" * 60)
print("✅ DEPLOYMENT COMPLETE!")
print("\nTry accessing:")
print("   • https://apiblockchain.io/home.html (direct access)")
print("   • https://apiblockchain.io/ (should redirect to home.html)")
print("\nIf root still shows Website Builder, contact One.com support:")
print("   'I want my custom home.html to be the default page'")

sftp.close()
transport.close()
