import requests, json, sys

def main():
    url = 'http://127.0.0.1:8000/create_session'
    payload = {'merchant_id':'merchant_test@example.com','amount':100,'mode':'payment'}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print('STATUS', r.status_code)
        try:
            print(json.dumps(r.json(), indent=2))
        except Exception:
            print(r.text)
    except Exception as e:
        print('ERROR', e)
        sys.exit(2)

if __name__ == '__main__':
    main()
