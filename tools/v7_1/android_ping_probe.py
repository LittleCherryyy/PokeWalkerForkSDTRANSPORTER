#!/usr/bin/env python3
"""RAM-only local Wi-Fi PING probe for the Android V18 direct-sync service.

Never sends a checkout, return, confirmation or game/save payload.
"""
import argparse
import socket
import struct
import time
import zlib

MAGIC = b"PWDSI001"
VERSION = 1
PORT = 30821
HEADER_SIZE = 88
PING = 4
OK = 0x80
ERROR = 0x7F
MAX_PAYLOAD = 65536


def make_ping() -> bytes:
    # magic[8], version u8, op u8, flags u16 BE, length u32 BE,
    # CRC32 u32 BE, session[32], trainer[36].
    frame = struct.pack(">8sBBHII32s36s",
                        MAGIC, VERSION, PING, 0, 0, 0, b"", b"")
    assert len(frame) == HEADER_SIZE
    return frame


def read_exact(sock: socket.socket, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            raise ConnectionError(f"Connection ended after {len(data)} of {count} bytes")
        data.extend(chunk)
    return bytes(data)


def read_reply(sock: socket.socket) -> tuple[int, bytes]:
    header = read_exact(sock, HEADER_SIZE)
    magic, version, op, flags, size, crc, session, trainer = struct.unpack(
        ">8sBBHII32s36s", header)
    if magic != MAGIC or version != VERSION:
        raise ValueError("Unexpected protocol magic or version")
    if flags != 0 or size > MAX_PAYLOAD:
        raise ValueError("Invalid flags or payload length")
    payload = read_exact(sock, size)
    if size and (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
        raise ValueError("Corrupted response checksum")
    if op not in (OK, ERROR):
        raise ValueError(f"Unexpected response operation: 0x{op:02x}")
    return op, payload


def probe(host: str, *, port: int = PORT, count: int = 3,
          timeout: float = 5.0) -> list[float]:
    if not (1 <= count <= 20):
        raise ValueError("Count must be between 1 and 20")
    durations = []
    with socket.create_connection((host, port), timeout=timeout) as peer:
        peer.settimeout(timeout)
        for _ in range(count):
            started = time.monotonic()
            peer.sendall(make_ping())
            op, response = read_reply(peer)
            if op == ERROR:
                raise RuntimeError("Android rejected PING: " + response[:200].decode(
                    "utf-8", errors="replace"))
            if response:
                raise ValueError("PING response unexpectedly includes a payload")
            durations.append((time.monotonic() - started) * 1000)
    return durations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("android_ip", help="phone hotspot gateway/IP reachable from this computer")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()
    if not (1 <= args.port <= 65535) or args.timeout <= 0:
        ap.error("Invalid port or timeout")
    print(f"Checking {args.android_ip}:{args.port} (PING only; no save access)")
    try:
        for i, ms in enumerate(probe(args.android_ip, port=args.port,
                                     count=args.count, timeout=args.timeout), 1):
            print(f"  PING {i}: OK ({ms:.1f} ms)")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"FAILED: {exc}")
        return 1
    print("PASS: Android V18 accepted repeated 88-byte DSi bridge PING frames.")
    print("NOTE: This does NOT prove resident Wi-Fi connectivity inside HGSS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
