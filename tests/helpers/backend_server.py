"""Tiny HTTP server helpers for backend integration tests."""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Iterator


@contextmanager
def backend_search_server(payload: dict | None = None, *, status: int = 200, raw_body: str | None = None) -> Iterator[tuple[str, list[dict]]]:
    requests: list[dict] = []
    response_payload = payload if payload is not None else {
        'schema_version': 'knowledge_search_response_v1',
        'status': 'NO_MATCH',
        'results': [],
        'trace': {},
        'diagnostics': [],
    }

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - stdlib handler API
            length = int(self.headers.get('Content-Length') or '0')
            body = self.rfile.read(length).decode('utf-8')
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = body
            requests.append({'path': self.path, 'headers': dict(self.headers), 'body': parsed})

            response_text = raw_body if raw_body is not None else json.dumps(response_payload, ensure_ascii=False)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response_text.encode('utf-8'))

        def do_GET(self):  # noqa: N802 - stdlib handler API
            requests.append({'path': self.path, 'headers': dict(self.headers), 'body': None})
            response_text = raw_body if raw_body is not None else json.dumps(response_payload, ensure_ascii=False)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response_text.encode('utf-8'))

        def log_message(self, format, *args):  # noqa: A002 - stdlib handler API
            return

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
