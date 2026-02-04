import hashlib
stored='0e3183c45e8ef9bc95fc8a2dc83f040149d2c7193312aa0740da9c0d50b1f439'
cands=['password','hunter2','merchant','merchant_test','test','123456','admin','letmein','secret','merchant_test@example.com']
for c in cands:
    h=hashlib.sha256(c.encode()).hexdigest()
    print(f"{c}: {h}", "MATCH" if h==stored else "")
