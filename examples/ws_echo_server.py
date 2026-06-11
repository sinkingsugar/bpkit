"""Minimal stdlib RFC6455 websocket server for testing the FLS WebSocketConnectionManager
recv path. No deps (the bundled UE python has no websockets lib).

- echoes every text frame back as  echo:<msg>
- pushes an unsolicited  tick:<n>  every 2s (proves server->client without a request)
- answers ping with pong; logs everything to stdout

Run:  & $BUNDLED_PYTHON examples/ws_echo_server.py [port]
"""
import socket, threading, base64, hashlib, struct, sys, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def log(*a):
    print("[ws]", *a, flush=True)


def handshake(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            return False
        data += chunk
    headers = {}
    for line in data.decode("latin1").split("\r\n")[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k.lower()] = v
    log("handshake headers:", headers)
    key = headers.get("sec-websocket-key")
    if not key:
        return False
    accept = base64.b64encode(hashlib.sha1((key + MAGIC).encode()).digest()).decode()
    resp = ("HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Accept: %s\r\n" % accept)
    proto = headers.get("sec-websocket-protocol")
    if proto:
        resp += "Sec-WebSocket-Protocol: %s\r\n" % proto.split(",")[0].strip()
    conn.sendall((resp + "\r\n").encode())
    return True


def send_frame(conn, payload, opcode=0x1):
    data = payload.encode() if isinstance(payload, str) else payload
    head = bytes([0x80 | opcode])
    n = len(data)
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack(">H", n)
    else:
        head += bytes([127]) + struct.pack(">Q", n)
    conn.sendall(head + data)


def read_frame(conn):
    hdr = conn.recv(2)
    if len(hdr) < 2:
        return None, None
    opcode = hdr[0] & 0x0F
    masked = hdr[1] & 0x80
    n = hdr[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", conn.recv(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", conn.recv(8))[0]
    mask = conn.recv(4) if masked else b"\x00" * 4
    data = b""
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    if masked:
        data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
    return opcode, data


def ticker(conn, stop):
    i = 0
    while not stop.is_set():
        time.sleep(2)
        i += 1
        try:
            send_frame(conn, "tick:%d" % i)
            log("pushed tick:%d" % i)
        except OSError:
            return


def client(conn, addr):
    log("conn from", addr)
    try:
        if not handshake(conn):
            log("handshake FAILED")
            return
        log("handshake OK")
        stop = threading.Event()
        threading.Thread(target=ticker, args=(conn, stop), daemon=True).start()
        while True:
            op, data = read_frame(conn)
            if op is None or op == 0x8:
                log("close (op=%s)" % op)
                break
            if op == 0x9:
                send_frame(conn, data, 0xA)
                log("ping -> pong")
                continue
            if op in (0x1, 0x2):
                txt = data.decode("utf8", "replace")
                log("RECV: %r" % txt)
                send_frame(conn, "echo:" + txt)
        stop.set()
    except OSError as e:
        log("sock err:", e)
    finally:
        conn.close()


srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", PORT))
srv.listen(4)
log("listening on 127.0.0.1:%d" % PORT)
while True:
    c, a = srv.accept()
    threading.Thread(target=client, args=(c, a), daemon=True).start()
