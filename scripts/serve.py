"""Loopback-only preview server; exposes only public design assets, never local state."""
import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.generate_daily import load_prompts, resolve_date
from scripts.local_state import JsonStateStore, MemoryStateStore
from scripts.rotation import build_local_payload


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/api/feed':
            source = parse_qs(parsed.query).get('source', ['auto'])[0]
            if source not in ('auto', 'curated', 'mock'):
                return self.send_error(400, 'Unknown source')
            try:
                cards = load_prompts()
                if source == 'mock':
                    store = MemoryStateStore()
                    fixture = ROOT / 'tests' / 'fixtures' / 'generation.json'
                    if fixture.exists():
                        state = store.read()
                        for i, card in enumerate(json.loads(fixture.read_text(encoding='utf-8'))['prompts']):
                            state['generated'].append({**card, 'id': f'mock-{i+1:03}', 'provenance': {'source': 'mock'}})
                        store.write(state)
                    payload = build_local_payload(cards, store, resolve_date(None), source)
                else:
                    store = JsonStateStore(ROOT / '.runtime/state.json')
                    with store.locked():
                        payload = build_local_payload(cards, store, resolve_date(None), source)
                data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (ValueError, OSError, RuntimeError) as error:
                self.send_error(503, 'Saved feed unavailable; static offline fallback is available')
            return
        path = unquote(parsed.path)
        if path == '/':
            self.send_response(302)
            self.send_header('Location', '/preview/')
            self.end_headers()
            return
        parts = Path(path.lstrip('/')).parts
        target = (ROOT / path.lstrip('/')).resolve()
        if not target.is_relative_to(ROOT) or any(p.startswith('.') for p in parts) or not parts or parts[0] not in ('preview', 'src', 'data', 'assets', 'public'):
            return self.send_error(404)
        # Encoded separators cannot bypass the allowlist or expose arbitrary files.
        if target.parts[len(ROOT.parts)] not in ('preview', 'src', 'data', 'assets', 'public'):
            return self.send_error(404)
        super().do_GET()

    def do_HEAD(self):
        # Avoid SimpleHTTPRequestHandler's unrestricted HEAD path.
        self.send_error(405)

    def list_directory(self, path):
        self.send_error(404)
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Local studio: http://127.0.0.1:{args.port}/preview/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
