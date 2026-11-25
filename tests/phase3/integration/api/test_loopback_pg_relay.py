import socket
import socketserver
import threading
import unittest
from loopback_pg_relay import LoopbackPGRelay


class Echo(socketserver.BaseRequestHandler):
    def handle(self):
        while data := self.request.recv(65536):
            self.request.sendall(data)


class EchoServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.server = EchoServer(("127.0.0.1", 0), Echo)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.relay = LoopbackPGRelay(self.server.server_address[1])
        self.addCleanup(self.relay.close)

    def exchange(self, data):
        with socket.create_connection(("127.0.0.1", self.relay.port), timeout=2) as client:
            client.sendall(data)
            received = b""
            while len(received) < len(data):
                chunk = client.recv(65536)
                if not chunk:
                    break
                received += chunk
            return received

    def test_binary_passthrough(self):
        payload = b"\x00\xff\x16\x03" * 200
        self.assertEqual(self.exchange(payload), payload)

    def test_pause_and_resume(self):
        self.assertEqual(self.exchange(b"before"), b"before")
        self.relay.pause()
        try:
            result = self.exchange(b"blocked")
        except (ConnectionError, OSError):
            result = b""
        self.assertEqual(result, b"")
        self.relay.resume()
        self.assertEqual(self.exchange(b"after"), b"after")

    def test_invalid_target(self):
        for value in (0, 65536, True, "5432"):
            with self.assertRaises(ValueError):
                LoopbackPGRelay(value)


if __name__ == "__main__":
    unittest.main()
