import socket
import struct
import threading
import unittest
from android_ping_probe import make_ping, read_reply, probe, MAGIC, VERSION, OK


class FrameTests(unittest.TestCase):
    def test_ping_frame_is_exactly_88_bytes(self):
        f = make_ping()
        self.assertEqual(len(f), 88)
        self.assertEqual(f[:10], b"PWDSI001"+bytes([1,4]))
        self.assertEqual(f[10:], bytes(78))

    def test_ok_reply(self):
        left, right = socket.socketpair()
        try:
            right.sendall(struct.pack(">8sBBHII32s36s",
                                      MAGIC, VERSION, OK, 0, 0, 0, b"", b""))
            self.assertEqual(read_reply(left), (OK, b""))
        finally:
            left.close()
            right.close()

    def test_reject_bad_magic(self):
        left, right = socket.socketpair()
        try:
            right.sendall(b"NOTMAGIC" + bytes(80))
            with self.assertRaises(ValueError):
                read_reply(left)
        finally:
            left.close()
            right.close()

    def test_three_pings_one_connection(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        failures = []
        def accept():
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(3)
                    for _ in range(3):
                        request = bytearray()
                        while len(request) < 88:
                            block = conn.recv(88 - len(request))
                            if not block:
                                raise EOFError("Client disconnected early")
                            request.extend(block)
                        if bytes(request) != make_ping():
                            raise AssertionError("Unexpected PING request")
                        conn.sendall(struct.pack(">8sBBHII32s36s",
                                                 MAGIC, VERSION, OK, 0, 0, 0, b"", b""))
            except Exception as e:
                failures.append(str(e))
            finally:
                server.close()
        t = threading.Thread(target=accept)
        t.start()
        try:
            durations = probe("127.0.0.1", port=port, count=3, timeout=3)
            self.assertEqual(len(durations), 3)
        finally:
            t.join(timeout=4)
        self.assertFalse(t.is_alive())
        self.assertFalse(failures, failures)


if __name__ == "__main__":
    unittest.main()
