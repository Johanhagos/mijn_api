import hashlib
h='0e3183c45e8ef9bc95fc8a2dc83f040149d2c7193312aa0740da9c0d50b1f439'
cands=['password','hunter2','test','merchant','merchant_test','123456','secret','letmein','admin','Pa$$w0rd','password123']
for c in cands:
    if hashlib.sha256(c.encode()).hexdigest()==h:
        print('MATCH',c)
        break
else:
    print('NO MATCH')
