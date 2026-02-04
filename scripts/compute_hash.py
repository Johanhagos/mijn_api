import hashlib
k = b'sk_test_local_automation'
print(hashlib.sha256(k).hexdigest())
