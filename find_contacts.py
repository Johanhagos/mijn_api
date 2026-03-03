import json
import os
from pathlib import Path

# Search for contacts.json
for root, dirs, files in os.walk('.'):
    if 'contacts.json' in files:
        file_path = Path(root) / 'contacts.json'
        print(f'Found: {file_path.resolve()}')
        contacts = json.loads(file_path.read_text())
        print(f'Total contacts: {len(contacts)}')
        print('\nLatest 3 contacts:')
        for contact in contacts[-3:]:
            print(f"  - {contact['name']} ({contact['email']}): {contact['subject']}")
        break
