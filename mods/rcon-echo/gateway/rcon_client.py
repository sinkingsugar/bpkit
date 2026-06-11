"""Minimal RCON client for the rcon-echo transport test (gateway side).

Speaks Source RCON (the de-facto protocol: SERVERDATA_AUTH=3 / EXECCOMMAND=2 /
RESPONSE_VALUE=0, little-endian framed) -- with a --raw fallback that sends
newline-terminated plaintext, in case Funcom's RconPlugin uses a bare text
protocol (its framing is not verifiable from DLL strings alone; whichever mode
gets "ECHO: ..." back is the answer, and gets recorded in the README).

Usage (any Python 3; no deps):
  python rcon_client.py --host 127.0.0.1 --port 25575 --password <pw> bpecho hello world
  python rcon_client.py --raw  --host 127.0.0.1 --port 25575 bpecho hello world
  python rcon_client.py ... help            # list the server's commands
"""
import argparse
import socket
import struct
import sys

SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0


def _send_packet(sock, req_id, ptype, body):
    payload = struct.pack("<ii", req_id, ptype) + body.encode("utf-8") + b"\x00\x00"
    sock.sendall(struct.pack("<i", len(payload)) + payload)


def _recv_packet(sock):
    raw = b""
    while len(raw) < 4:
        chunk = sock.recv(4 - len(raw))
        if not chunk:
            raise ConnectionError("server closed the connection")
        raw += chunk
    (size,) = struct.unpack("<i", raw)
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ConnectionError("server closed mid-packet")
        data += chunk
    req_id, ptype = struct.unpack("<ii", data[:8])
    body = data[8:-2].decode("utf-8", errors="replace")
    return req_id, ptype, body


def source_rcon(host, port, password, command, timeout):
    with socket.create_connection((host, port), timeout=timeout) as s:
        _send_packet(s, 1, SERVERDATA_AUTH, password)
        # auth may be preceded by an empty RESPONSE_VALUE packet (Source quirk)
        rid, ptype, _ = _recv_packet(s)
        if ptype == SERVERDATA_RESPONSE_VALUE:
            rid, ptype, _ = _recv_packet(s)
        if rid == -1:
            raise PermissionError("RCON auth refused (bad password?)")
        _send_packet(s, 2, SERVERDATA_EXECCOMMAND, command)
        rid, ptype, body = _recv_packet(s)
        return body


def raw_text(host, port, command, timeout):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall((command + "\n").encode("utf-8"))
        s.settimeout(timeout)
        out = b""
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                out += chunk
        except socket.timeout:
            pass
        return out.decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=25575)
    ap.add_argument("--password", default="")
    ap.add_argument("--raw", action="store_true", help="newline-terminated plaintext mode")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("command", nargs="+", help="the RCON command + args")
    a = ap.parse_args()
    cmd = " ".join(a.command)
    try:
        if a.raw:
            body = raw_text(a.host, a.port, cmd, a.timeout)
        else:
            body = source_rcon(a.host, a.port, a.password, cmd, a.timeout)
    except Exception as e:
        print("FAIL: %s: %s" % (type(e).__name__, e))
        sys.exit(1)
    print("RESPONSE: %r" % body)
    sys.exit(0 if body else 2)


if __name__ == "__main__":
    main()
