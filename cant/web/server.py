"""Tiny stdlib HTTP server for the Binary Cant UI (no external dependencies, no CDN)."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .api import Api, ApiError

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY = 8 * 1024 * 1024


def make_handler(api):
    routes = {"/api/en2cant": api.en2cant, "/api/cant2en": api.cant2en, "/api/encode": api.encode,
              "/api/decode": api.decode, "/api/lexicon": api.lexicon, "/api/distance": api.distance,
              "/api/meta": api.meta}

    class Handler(BaseHTTPRequestHandler):
        server_version = "BinaryCant/2.2"

        def log_message(self, fmt, *args):  # quiet by default; set CANT_LOG=1 to see requests
            if os.environ.get("CANT_LOG"):
                sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _send(self, status, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _dispatch(self, path, req):
            fn = routes.get(path)
            if fn is None:
                return self._send(404, {"error": f"no such endpoint {path}"})
            try:
                return self._send(200, fn(req))
            except ApiError as ex:
                return self._send(400, {"error": str(ex)})
            except Exception as ex:  # never kill the server on a bad request
                return self._send(500, {"error": f"internal error: {type(ex).__name__}: {ex}"})

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path.startswith("/api/"):
                req = {k: v[-1] for k, v in parse_qs(u.query).items()}
                return self._dispatch(u.path, req)
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"error": "request too large"})
            raw = self.rfile.read(n) if n else b"{}"
            try:
                req = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(req, dict):
                    raise ValueError
            except ValueError:
                return self._send(400, {"error": "request body must be a JSON object"})
            return self._dispatch(u.path, req)

    return Handler


def make_server(host="127.0.0.1", port=8000, lex=None):
    return ThreadingHTTPServer((host, port), make_handler(Api(lex)))


def serve(host="127.0.0.1", port=8000, lex=None):
    httpd = make_server(host, port, lex)
    print(f"Binary Cant UI on http://{host}:{httpd.server_address[1]}/  (Ctrl-C to stop)", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
