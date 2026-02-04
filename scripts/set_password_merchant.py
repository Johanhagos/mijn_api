import json
from pathlib import Path
from passlib.context import CryptContext

DATA_DIR = Path(r"c:\Users\gebruiker\Desktop\mijn_api")
USERS_FILE = DATA_DIR / "users.json"

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

email = "merchant_test@example.com"
new_password = "Nathnael1997&"

if not USERS_FILE.exists():
    print("users.json not found at", USERS_FILE)
    raise SystemExit(1)

with open(USERS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

found = False
for u in data:
    if u.get("name") == email:
        u["password"] = pwd_ctx.hash(new_password)
        found = True
        break

if not found:
    print("User not found:", email)
    raise SystemExit(1)

with open(USERS_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("Password updated for", email)
