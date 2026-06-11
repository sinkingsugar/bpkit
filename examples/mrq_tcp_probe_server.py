"""TCP probe server for the MoviePipelineExecutor socket channel (framing unknown
going in, so: hexdump EVERYTHING received, then echo each chunk back verbatim after
0.5s -- framing-agnostic round-trip; if the executor's framing is symmetric the echo
must fire its SocketMessageRecieved delegate).

Run:  & $BUNDLED_PYTHON examples/mrq_tcp_probe_server.py [port=9777]
"""
import socket, threading, sys, time

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9777


def log(*a):
    print("[tcp]", *a, flush=True)


def hexdump(b):
    for i in range(0, len(b), 16):
        chunk = b[i:i + 16]
        hx = " ".join("%02x" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        log("  %04x  %-48s %s" % (i, hx, asc))


def client(conn, addr):
    log("conn from", addr)
    try:
        while True:
            data = conn.recv(65536)
            if not data:
                log("disconnect", addr)
                return
            log("RECV %d bytes:" % len(data))
            hexdump(data)
            time.sleep(0.5)
            conn.sendall(data)
            log("echoed %d bytes back" % len(data))
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
