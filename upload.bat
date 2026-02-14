# FileZilla automated upload script
cd %AppData%\FileZilla
mkdir sitemanager 2>nul

echo Uploading to One.com...
timeout /t 2

# The file is ready at: c:\Users\gebruiker\Desktop\mijn_api\webshop_for_upload\index.html
# Destination: ssh.cruerobt5.service.one:22 public_html/index.html
