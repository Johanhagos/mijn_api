import os
import uvicorn

os.environ.setdefault('JWT_SECRET_KEY', 'devsecret')
os.environ.setdefault('DATA_DIR', r'C:\Users\gebruiker\Desktop\mijn_api')

if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8802, log_level='info')
