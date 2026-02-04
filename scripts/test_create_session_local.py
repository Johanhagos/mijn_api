from fastapi.testclient import TestClient
import json
import sys
import os
from pathlib import Path

# Ensure repo root on sys.path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

# Force hosted checkout base to localhost for testing screenshots
os.environ.setdefault('HOSTED_CHECKOUT_BASE', 'http://127.0.0.1:8000')

import main

client = TestClient(main.app)


def main_test():
    payload = {'merchant_id': 'merchant_test@example.com', 'amount': 100, 'mode': 'payment'}
    headers = {'x-api-key': 'sk_test_local_automation'}
    r = client.post('/create_session', json=payload, headers=headers)
    print('STATUS', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


if __name__ == '__main__':
    main_test()
