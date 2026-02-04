import json
import sys
from urllib import request, error

data = json.dumps({'name':'merchant_test@example.com','password':'merchant123'}).encode('utf-8')
req = request.Request('http://127.0.0.1:8001/login', data=data, headers={'Content-Type':'application/json'})
try:
    with request.urlopen(req, timeout=5) as r:
        print(r.status)
        print(r.read().decode())
except error.HTTPError as e:
    try:
        print(e.code)
        print(e.read().decode())
    except:
        print('HTTPError', e)
    sys.exit(1)
except Exception as e:
    print('ERROR', e)
    sys.exit(1)
