import paramiko

HOSTNAME = "ssh.cruerobt5.service.one"
USERNAME = "cruerobt5_ssh"
PASSWORD = "Johanahagos1992&"
REMOTE_PATH = "/webroots/dae9921c/"

print("🔍 CHECKING SERVER FILES")
print("=" * 60)

transport = paramiko.Transport((HOSTNAME, 22))
transport.connect(username=USERNAME, password=PASSWORD)
sftp = paramiko.SFTPClient.from_transport(transport)

print(f"✅ Connected to {HOSTNAME}")
print(f"\n📂 Files in {REMOTE_PATH}:\n")

try:
    files = sftp.listdir_attr(REMOTE_PATH)
    for file in files:
        size_kb = file.st_size / 1024
        file_type = "📁 DIR " if file.st_mode & 0o040000 else "📄 FILE"
        print(f"{file_type} {file.filename:30} {size_kb:>8.1f} KB")
    
    print("\n" + "=" * 60)
    print("\n✅ Your files ARE on the server!")
    print("\nTry accessing directly:")
    print("   • https://apiblockchain.io/index.html")
    print("   • https://apiblockchain.io/home.html")
    print("   • https://apiblockchain.io/checkout.html")
    print("\nIf 404 persists, One.com Website Builder is blocking ALL custom files.")
    print("\n⚠️ SOLUTION: Contact One.com support:")
    print("   'I need to disable Website Builder and use my custom HTML files'")
    
except Exception as e:
    print(f"❌ Error: {e}")

sftp.close()
transport.close()
