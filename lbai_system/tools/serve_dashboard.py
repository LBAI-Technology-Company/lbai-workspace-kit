#!/usr/bin/env python3
"""Serve the LBAI workspace root so workspace_dashboard.html can fetch Markdown files."""

from __future__ import annotations

import argparse
import http.server
import socketserver
import webbrowser
from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description='Serve workspace_dashboard.html over local HTTP.')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true', help='Do not open the browser automatically.')
    args = parser.parse_args()

    root = workspace_root()
    handler = lambda *handler_args, **handler_kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *handler_args,
        directory=str(root),
        **handler_kwargs,
    )

    url = f'http://127.0.0.1:{args.port}/workspace_dashboard.html'
    with socketserver.TCPServer(('127.0.0.1', args.port), handler) as httpd:
        print(f'Serving {root}')
        print(f'Dashboard: {url}')
        print('Press Ctrl+C to stop.')
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
