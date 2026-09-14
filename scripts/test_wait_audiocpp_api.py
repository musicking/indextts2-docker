"""Regression coverage for reset-on-start, timeout, and container exit."""
import contextlib
import http.server
from pathlib import Path
import socket
import struct
import sys
import threading
import unittest
from unittest.mock import patch

from wait_audiocpp_api import wait_for_api


@contextlib.contextmanager
def api_fixture(resets):
    class Handler(http.server.BaseHTTPRequestHandler):
        attempts = 0

        def do_GET(self):
            type(self).attempts += 1
            if self.attempts <= resets:
                # TCP RST, matching CI curl error 56 rather than an empty reply.
                layout = "hh" if sys.platform == "win32" else "ii"
                self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                           struct.pack(layout, 1, 0))
                self.connection.close()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/health"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class ReadinessTests(unittest.TestCase):
    def test_workflow_uses_bounded_container_aware_check(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/audio-cpp-publish.yml").read_text()
        self.assertIn("python3 scripts/wait_audiocpp_api.py --container api-smoke", workflow)

    def test_retries_startup_disconnect(self):
        with api_fixture(2) as url:
            wait_for_api(url, timeout=2, interval=0.01)

    def test_persistent_failure_is_bounded(self):
        with api_fixture(1000) as url:
            with self.assertRaises(TimeoutError):
                wait_for_api(url, timeout=0.1, interval=0.01)

    def test_container_exit_fails_immediately(self):
        with patch("wait_audiocpp_api.subprocess.check_output",
                   return_value='{"Running":false,"ExitCode":139}'):
            with self.assertRaisesRegex(RuntimeError, "139"):
                wait_for_api("http://127.0.0.1:1/health", container="api-smoke")


if __name__ == "__main__":
    unittest.main()
