import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

url = 'http://127.0.0.1:8002/checkout'
headers = {
    'X-API-Key': 'sk_test_local_automation',
    'Content-Type': 'application/json'
}
body = json.dumps({'amount': 10, 'mode': 'test'}).encode('utf-8')
req = Request(url, data=body, headers=headers, method='POST')
try:
    with urlopen(req, timeout=10) as resp:
        print('STATUS', resp.status)
        data = resp.read().decode('utf-8')
        print(data)
except HTTPError as e:
    print('HTTP ERROR', e.code)
    try:
        print(e.read().decode())
    except:
        pass
except URLError as e:
    print('URL ERROR', e.reason)
except Exception as e:
    print('ERROR', e)
