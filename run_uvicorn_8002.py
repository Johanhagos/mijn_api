import os
import subprocess
from pathlib import Path

BASE = Path(r"C:\Users\gebruiker\Desktop\mijn_api")
VENV_PY = BASE / "venv2" / "Scripts" / "python.exe"

os.environ['JWT_SECRET_KEY'] = 'devsecret'
os.environ['DATA_DIR'] = str(BASE)
os.environ['ALLOW_DEBUG'] = '1'

# Start uvicorn as a background process
cmd = [str(VENV_PY), '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8002']
print('Starting:', ' '.join(cmd))
subprocess.Popen(cmd, cwd=str(BASE))
print('uvicorn launched on port 8002')
