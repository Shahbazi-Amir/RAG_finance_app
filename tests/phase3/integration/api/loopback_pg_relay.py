"""Test-only loopback relay for a reversible PG connection outage.

Never modifies the database. TLS is passed through unchanged; the client
continues to verify the original PostgreSQL server certificate.
"""
import select
import socket
import socketserver
import threading


class _RelayHandler(socketserver.BaseRequestHandler):
    def handle(self):
        if self.server.paused.is_set():
            return
        try:
            with socket.create_connection(("127.0.0.1", self.server.target_port), timeout=2) as upstream:
                upstream.settimeout(2)
                self.request.settimeout(2)
                peers = {upstream: self.request, self.request: upstream}
                while not self.server.paused.is_set():
                    readable, _, _ = select.select(list(peers), [], [], .1)
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        peers[source].sendall(data)
        except (OSError, ValueError):
            return


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True


class LoopbackPGRelay:
    def __init__(self, target_port=5432):
        if type(target_port) is not int or not 1 <= target_port <= 65535:
            raise ValueError("invalid loopback target port")
        self._server = _Server(("127.0.0.1", 0), _RelayHandler)
        self._server.target_port = target_port
        self._server.paused = threading.Event()
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self):
        return self._server.server_address[1]

    def pause(self):
        self._server.paused.set()

    def resume(self):
        self._server.paused.clear()

    def close(self):
        self.pause()
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
