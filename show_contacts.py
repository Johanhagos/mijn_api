import json
from pathlib import Path

contacts = json.loads(Path('C:/tmp/contacts.json').read_text())
print(f'Total Contacts: {len(contacts)}')
print('\nRecent submissions:')
print('-' * 80)
for i, contact in enumerate(contacts[-3:], 1):
    print(f'{i}. {contact["name"]} ({contact["email"]})')
    print(f'   Subject: {contact["subject"]}')
    print(f'   Message: {contact["message"][:60]}...')
    print(f'   Saved at: {contact["created_at"]}')
    print()
