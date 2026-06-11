"""Interactive console server for the MrqEcho channel. The cooked game's
BP_MrqEchoController connects OUT to this (127.0.0.1:9777) and speaks the
MoviePipelineExecutor framing: 4-byte LITTLE-ENDIAN length prefix + UTF-8.

NOTE: plain netcat does NOT work for sending -- your typed bytes get read as a
length prefix and the game waits forever. This console frames for you.

Run with any Python 3 (stdlib only):   python mrq_console.py [port=9777]
Then type lines; each is pushed to the game (HUD shows "MRQ RECV: <line>" and
the game acks back "ack:<line>").
"""
import socket, struct, sys, threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9777
clients = []
lock = threading.Lock()


def log(*a):
    print(*a, flush=True)


def reader(conn, addr):
    buf = b""
    try:
        while True:
            d = conn.recv(65536)
            if not d:
                break
            buf += d
            while len(buf) >= 4:
                n = struct.unpack("<I", buf[:4])[0]
                if n > 16 * 1024 * 1024:
                    log("[mrq] %s: insane frame length %d -- dropping conn" % (addr, n))
                    return
                if len(buf) < 4 + n:
                    break
                msg = buf[4:4 + n].decode("utf8", "replace")
                buf = buf[4 + n:]
                log("GAME> %s" % msg)
    except OSError:
        pass
    finally:
        with lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        log("[mrq] %s disconnected" % (addr,))


def acceptor(srv):
    while True:
        c, a = srv.accept()
        log("[mrq] game connected from %s" % (a,))
        with lock:
            clients.append(c)
        threading.Thread(target=reader, args=(c, a), daemon=True).start()


srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", PORT))
srv.listen(4)
log("[mrq] console listening on 127.0.0.1:%d -- type lines to push to the game" % PORT)
threading.Thread(target=acceptor, args=(srv,), daemon=True).start()

for line in sys.stdin:
    line = line.rstrip("\r\n")
    if not line:
        continue
    data = line.encode("utf8")
    frame = struct.pack("<I", len(data)) + data
    with lock:
        live = list(clients)
    if not live:
        log("[mrq] (no game connected)")
        continue
    for c in live:
        try:
            c.sendall(frame)
        except OSError:
            pass
    log("PUSH> %s  (%d client%s)" % (line, len(live), "s" if len(live) != 1 else ""))
