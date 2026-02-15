#!/usr/bin/env python3
"""
Migrate script: Add 'country' field to existing merchants who don't have it.
This ensures they have a default VAT rate for tax calculations.
"""

import json
import os
from pathlib import Path

# Locate users.json
script_dir = Path(__file__).parent
repo_root = script_dir.parent
users_file = repo_root / 'users.json'

print(f"Looking for users.json at: {users_file}")

if not users_file.exists():
    print("❌ users.json not found!")
    exit(1)

# Load users
with open(users_file, 'r') as f:
    users = json.load(f)

print(f"✅ Loaded {len(users)} users")

# Update users without country
updated_count = 0
for user in users:
    if not user.get('country'):
        # Default to Netherlands (NL) if not specified
        user['country'] = 'NL'
        updated_count += 1
        print(f"   → Updated user '{user.get('name', 'Unknown')}' with country=NL")

print(f"\n✅ Updated {updated_count} users with default country")

# Save updated users
with open(users_file, 'w') as f:
    json.dump(users, f, indent=2)

print(f"✅ Saved {len(users)} users to users.json")
print("\nNow each merchant can:")
print("  1. Ask the AI: 'What is my VAT rate?'")
print("  2. Update their country in profile settings")
print("  3. Get correct tax calculations based on their location")
