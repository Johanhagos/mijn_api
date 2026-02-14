#!/bin/bash
# Upload index.html to One.com

expect << EOF
spawn sftp -P 22 cruerobt5_ssh@ssh.cruerobt5.service.one

expect "password:"
send "Johanahagos1992&\r"

expect "sftp>"
send "cd public_html\r"

expect "sftp>"
send "put c:/Users/gebruiker/Desktop/mijn_api/webshop_for_upload/index.html index.html\r"

expect "sftp>"
send "exit\r"

EOF
