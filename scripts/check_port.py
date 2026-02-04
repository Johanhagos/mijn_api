import socket
import sys

def check(host='127.0.0.1', port=8802):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, port))
        print('TCP_OK')
        req = b'GET / HTTP/1.1\r\nHost: %b\r\nConnection: close\r\n\r\n' % host.encode()
        s.sendall(req)
        data = s.recv(1024)
        if data:
            first = data.splitlines()[0]
            print('RESP_LINE:', first.decode(errors='replace'))
        else:
            print('NO_RESPONSE_BODY')
    except Exception as e:
        print('ERROR', e)
        return 2
    finally:
        s.close()
    return 0

if __name__ == '__main__':
    port = 8802
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            pass
    sys.exit(check(port=port))
