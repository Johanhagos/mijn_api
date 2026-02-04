import urllib.request, json

url = 'http://127.0.0.1:8000/checkout'
headers = {'X-API-Key': 'test_sk_merchant_local', 'Content-Type': 'application/json'}
body = json.dumps({'amount': 10, 'mode': 'test'}).encode()
req = urllib.request.Request(url, data=body, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        print(r.status)
        print(r.read().decode())
except Exception as e:
    print('ERROR', e)
