import subprocess
import sys
import time
import socket
import os

def find_pids_port(port=8000):
    try:
        out = subprocess.check_output(['netstat','-ano'], universal_newlines=True)
    except Exception as e:
        print('ERROR netstat failed', e)
        return []
    pids = set()
    for line in out.splitlines():
        if f':{port} ' in line or f':{port}\t' in line or f':{port}\r' in line:
            parts = line.split()
            if parts:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(int(pid))
    return list(pids)


def kill_pids(pids):
    for pid in pids:
        try:
            print('Killing PID', pid)
            subprocess.check_call(['taskkill','/PID',str(pid),'/F'])
        except Exception as e:
            print('Failed to kill', pid, e)


def start_uvicorn(port=8000):
    env = os.environ.copy()
    env.setdefault('JWT_SECRET_KEY','devsecret')
    env.setdefault('DATA_DIR', r'C:\Users\gebruiker\Desktop\mijn_api')
    cmd = [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', str(port)]
    print('Starting:', ' '.join(cmd))
    p = subprocess.Popen(cmd, env=env)
    return p


def check_port(port=8000, timeout=3):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(('127.0.0.1', port))
        s.sendall(b'GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
        data = s.recv(1024)
        if data:
            print('RESP_LINE:', data.splitlines()[0].decode(errors='replace'))
            return True
        else:
            print('NO_RESPONSE')
            return False
    except Exception as e:
        print('TCP_ERROR', e)
        return False
    finally:
        s.close()


if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            pass
    pids = find_pids_port(port)
    if pids:
        print('Found PIDs:', pids)
        kill_pids(pids)
        time.sleep(1)
    else:
        print('No processes found on port', port)
    proc = start_uvicorn(port)
    print('uvicorn started PID', proc.pid)
    time.sleep(2)
    ok = check_port(port)
    if not ok:
        print('Server did not respond on port', port)
        sys.exit(2)
    print('Server is up on port', port)
    sys.exit(0)
