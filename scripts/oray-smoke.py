"""Run the target ELF in QEMU: SOCKS5 TCP forwarding and SS AEAD forwarding."""
import contextlib
import http.server
import pathlib
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise RuntimeError("unexpected EOF")
        data += part
    return data


def request(port, target):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(b"\x05\x01\x00")
        assert recv_exact(sock, 2) == b"\x05\x00"
        sock.sendall(b"\x05\x01\x00\x01\x7f\x00\x00\x01" + struct.pack("!H", target))
        reply = recv_exact(sock, 4)
        assert reply[:3] == b"\x05\x00\x00", reply
        address_size = {1: 4, 4: 16}.get(reply[3])
        if reply[3] == 3:
            address_size = recv_exact(sock, 1)[0]
        assert address_size is not None
        recv_exact(sock, address_size + 2)
        sock.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
        response = b""
        while chunk := sock.recv(4096):
            response += chunk
        assert b"200 OK" in response and b"oray-smoke-ok" in response, response[:200]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"oray-smoke-ok")

    def log_message(self, *_):
        pass


binary = str(pathlib.Path(sys.argv[1]).resolve())
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
processes = []
with tempfile.TemporaryFile() as log:
    def start(*args):
        process = subprocess.Popen(["qemu-mipsel", "-cpu", "24KEc", binary, *args], stdout=log, stderr=log)
        processes.append(process)
        return process

    def wait_ready(process, port):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"glider exited: {process.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("listener did not become ready")

    try:
        socks = free_port()
        process = start("-listen", f"socks5://127.0.0.1:{socks}", "-check", "disable")
        wait_ready(process, socks)
        request(socks, server.server_port)
        print("PASS: SOCKS5 TCP forwarding on MIPS 24KEc")
        ss = free_port()
        ss_url = f"ss://chacha20-ietf-poly1305:oray-smoke-test@127.0.0.1:{ss}"
        process = start("-listen", ss_url, "-check", "disable")
        wait_ready(process, ss)
        chained = free_port()
        process = start("-listen", f"socks5://127.0.0.1:{chained}", "-forward", ss_url, "-check", "disable")
        wait_ready(process, chained)
        request(chained, server.server_port)
        print("PASS: SOCKS5 -> Shadowsocks AEAD -> HTTP on MIPS 24KEc")
    except Exception:
        log.seek(0)
        print(log.read().decode(errors="replace"), file=sys.stderr)
        raise
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=3)
            if process.poll() is None:
                process.kill()
                process.wait()
        server.shutdown()
