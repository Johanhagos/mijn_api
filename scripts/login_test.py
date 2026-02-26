import requests
import sys


def _run():
    try:
        r = requests.post(
            "http://127.0.0.1:8001/login",
            json={"name": "merchant_test@example.com", "password": "merchant123"},
            timeout=5,
        )
        print(r.status_code)
        print(r.text)
    except Exception as e:
        print("ERROR", e)
        sys.exit(1)


if __name__ == "__main__":
    _run()
