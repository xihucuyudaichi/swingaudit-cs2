"""Cloud container entrypoint for ModelScope Studio / Docker (0.0.0.0:7860).

Serves compiled static frontend (dist/) and all /api/* routes from a single port,
keeping backend/server.py and backend/lab_provider.py untouched.
Features:
- Environment variable / Secret injection (ROUND_LAB_BASE_URL, ROUND_LAB_API_KEY)
- Pre-computed Gzip compression for large read-only JSON endpoints (/api/bootstrap ~87MB -> ~8MB)
- Per-visitor isolated SQLite research records
- Same-origin POST handling and concurrency guard for /api/agent
"""
from __future__ import annotations

import contextvars
import gzip
import hashlib
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Preserve tracked completeness-report.json byte-for-byte during server import
_comp_path = ROOT / 'data/completeness-report.json'
_comp_orig = _comp_path.read_bytes() if _comp_path.exists() else None

import lab_provider
import research
import server

if _comp_orig is not None:
    try:
        _comp_path.write_bytes(_comp_orig)
    except OSError:
        pass

_orig_read_config = lab_provider.read_config


def _cloud_read_config():
    env_base = (os.environ.get('ROUND_LAB_BASE_URL') or '').strip()
    env_key = (os.environ.get('ROUND_LAB_API_KEY') or '').strip()
    if env_base and env_key:
        try:
            timeout = float(os.environ.get('ROUND_LAB_TIMEOUT_SECONDS', '60'))
        except ValueError:
            timeout = 60.0
        try:
            max_tokens = int(os.environ.get('ROUND_LAB_MAX_TOKENS', '8192'))
        except ValueError:
            max_tokens = 8192
        return {
            'base_url': env_base,
            'api_key': env_key,
            'timeout_seconds': timeout,
            'max_tokens': max_tokens,
        }
    return _orig_read_config()


lab_provider.read_config = _cloud_read_config

VISITOR_SESSION = contextvars.ContextVar('visitor_session', default='public_visitor')


def _resolve_visitor_dir() -> Path:
    custom = (os.environ.get('ROUND_VISITOR_DATA_DIR') or '').strip()
    if custom:
        p = Path(custom)
    elif Path('/mnt/workspace').is_dir() and os.access('/mnt/workspace', os.W_OK):
        p = Path('/mnt/workspace/round-visitor-data')
    else:
        p = Path(tempfile.gettempdir()) / 'round-observatory-visitors'
    p.mkdir(parents=True, exist_ok=True)
    return p


VISITOR_DIR = _resolve_visitor_dir()
_orig_db_path = research.db_path
research.db_path = lambda: _orig_db_path() if os.environ.get('ROUND_RESEARCH_DB') else (VISITOR_DIR / f'{VISITOR_SESSION.get()}.sqlite3')

AGENT_SEMAPHORE = threading.BoundedSemaphore(int(os.environ.get('ROUND_AGENT_CONCURRENCY', '3')))

# Pre-build Gzip cache for heavy read-only JSON responses
GZIP_CACHE: dict[str, tuple[bytes, bytes]] = {}
BOOTSTRAP_CACHE: dict[str, tuple[bytes, bytes]] = {}
BOOTSTRAP_LOCK = threading.Lock()


def _encode_pair(obj) -> tuple[bytes, bytes]:
    raw = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8')
    gz = gzip.compress(raw, compresslevel=6)
    return raw, gz


def warmup_caches():
    model_obj = json.loads((ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
    static_endpoints = {
        '/api/history': server.DATA,
        '/api/model': model_obj,
        '/api/roles': server.ROLE_REPORT,
        '/api/rules': {
            'rules': server.RULES_CORPUS,
            'ontology': server.ONTOLOGY,
            'event_weights': server.EVENT_WEIGHTS,
        },
        '/api/coverage': server.AUDIT,
        '/api/sources': server.SOURCES,
    }
    for path, payload in static_endpoints.items():
        GZIP_CACHE[path] = _encode_pair(payload)
    # Pre-warm default fast & full bootstrap with empty visitor records
    _get_fast_bootstrap_pair('2026', [])
    _get_bootstrap_pair([])


def _get_bootstrap_pair(records: list) -> tuple[bytes, bytes]:
    rec_key = hashlib.sha256(
        json.dumps(records, ensure_ascii=False, sort_keys=True).encode('utf-8')
    ).hexdigest()
    with BOOTSTRAP_LOCK:
        cached = BOOTSTRAP_CACHE.get(rec_key)
        if cached is not None:
            return cached
    model_obj = json.loads((ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
    payload = {
        'data': server.DATA,
        'report': model_obj,
        'roles': server.ROLE_REPORT,
        'rules': server.RULES_CORPUS,
        'ontology': server.ONTOLOGY,
        'event_weights': server.EVENT_WEIGHTS,
        'coverage': server.AUDIT,
        'sources': server.SOURCES,
        'records': records,
    }
    pair = _encode_pair(payload)
    with BOOTSTRAP_LOCK:
        if len(BOOTSTRAP_CACHE) >= 16:
            BOOTSTRAP_CACHE.clear()
        BOOTSTRAP_CACHE[rec_key] = pair
    return pair



FAST_BOOTSTRAP_CACHE: dict[str, tuple[bytes, bytes]] = {}


def _build_fast_data(full_years: set[str]) -> dict:
    seasons = {}
    for y, sv in server.DATA.get('seasons', {}).items():
        if y in full_years:
            seasons[y] = sv
        else:
            seasons[y] = {
                'rows': sv.get('rows', 0),
                'players': [
                    {
                        k: p[k]
                        for k in (
                            'id', 'name', 'year', 'maps', 'rating_estimate',
                            'mvp', 'evp', 'official_rank', 'team', 'country',
                            'cohort_tier', 'opponents', 'identity_status', 'source_ids'
                        )
                        if k in p
                    }
                    | {'events': []}
                    for p in sv.get('players', [])
                ],
                'events': [
                    {'name': e['name'], 'year': e.get('year'), 'tier': e.get('tier'), 'players': []}
                    for e in sv.get('events', [])
                ],
            }
    return {'meta': server.DATA.get('meta'), 'seasons': seasons}


def _build_fast_roles(full_years: set[str]) -> dict:
    seasons = {}
    for y, rv in (server.ROLE_REPORT.get('seasons') or {}).items():
        if y in full_years:
            seasons[y] = rv
        else:
            seasons[y] = {k: v for k, v in rv.items() if k != 'players'} | {'players': []}
    return {k: v for k, v in server.ROLE_REPORT.items() if k != 'seasons'} | {'seasons': seasons}


def _get_fast_bootstrap_pair(target_year: str, records: list) -> tuple[bytes, bytes]:
    full_years = {'2025', '2026', str(target_year or '2026')}
    cache_key = hashlib.sha256(
        json.dumps({'years': sorted(full_years), 'records': records}, ensure_ascii=False, sort_keys=True).encode('utf-8')
    ).hexdigest()
    with BOOTSTRAP_LOCK:
        cached = FAST_BOOTSTRAP_CACHE.get(cache_key)
        if cached is not None:
            return cached
    model_obj = json.loads((ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
    payload = {
        '_partial': True,
        'data': _build_fast_data(full_years),
        'report': model_obj,
        'roles': _build_fast_roles(full_years),
        'rules': server.RULES_CORPUS,
        'ontology': server.ONTOLOGY,
        'event_weights': server.EVENT_WEIGHTS,
        'coverage': server.AUDIT,
        'sources': server.SOURCES,
        'records': records,
    }
    pair = _encode_pair(payload)
    with BOOTSTRAP_LOCK:
        if len(FAST_BOOTSTRAP_CACHE) >= 16:
            FAST_BOOTSTRAP_CACHE.clear()
        FAST_BOOTSTRAP_CACHE[cache_key] = pair
    return pair


def _find_static_root() -> Path:
    for candidate in (
        ROOT / 'dist',
        ROOT / '.planning/2026-11-02-sites-deploy/public-dist',
    ):
        if (candidate / 'index.html').is_file():
            return candidate.resolve()
    return (ROOT / 'dist').resolve()


STATIC_ROOT = _find_static_root()


class CloudHandler(server.Handler):
    def _extract_visitor_id(self) -> str:
        header_val = (self.headers.get('X-Demo-Session') or '').strip()
        if re.fullmatch(r'[a-zA-Z0-9_-]{4,64}', header_val):
            return header_val
        cookie = self.headers.get('Cookie') or ''
        m = re.search(r'(?:^|;\s*)round_visitor=([a-zA-Z0-9_-]{4,64})', cookie)
        if m:
            return m.group(1)
        client_ip = (
            self.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or (self.client_address[0] if self.client_address else 'anon')
        )
        return 'v_' + hashlib.sha256(client_ip.encode('utf-8')).hexdigest()[:16]

    def _accepts_gzip(self) -> bool:
        enc = (self.headers.get('Accept-Encoding') or '').lower()
        return 'gzip' in enc

    def _send_bytes(self, status: int, raw: bytes, gz: bytes | None = None, content_type: str = 'application/json; charset=utf-8', cache_control: str = 'no-store'):
        use_gz = gz is not None and self._accepts_gzip()
        body = gz if use_gz else raw
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', cache_control)
            self.send_header('Vary', 'Accept-Encoding')
            if use_gz:
                self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def send(self, status, obj):
        raw = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf-8')
        gz = gzip.compress(raw, compresslevel=6) if len(raw) > 4096 else None
        self._send_bytes(status, raw, gz)

    def do_GET(self):
        token = VISITOR_SESSION.set(self._extract_visitor_id())
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path in GZIP_CACHE:
                raw, gz = GZIP_CACHE[path]
                return self._send_bytes(200, raw, gz)
            if path == '/api/bootstrap':
                records = research.get_records()
                if (self.headers.get('X-Bootstrap-Mode') or '').lower() == 'fast':
                    req_year = (self.headers.get('X-Bootstrap-Year') or '2026').strip()
                    raw, gz = _get_fast_bootstrap_pair(req_year, records)
                else:
                    raw, gz = _get_bootstrap_pair(records)
                return self._send_bytes(200, raw, gz)
            if path.startswith('/api/'):
                return super().do_GET()

            # Serve compiled frontend static files
            rel = urllib.parse.unquote(path).lstrip('/')
            target = (STATIC_ROOT / rel).resolve()
            if not target.is_relative_to(STATIC_ROOT):
                return self.send(403, {'error': 'Forbidden'})
            if target.is_dir():
                target = target / 'index.html'
            if not target.is_file():
                # SPA fallback to index.html for non-asset routes
                if not path.startswith('/assets/') and (STATIC_ROOT / 'index.html').is_file():
                    target = STATIC_ROOT / 'index.html'
                else:
                    return self.send(404, {'error': 'Not found'})

            content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
            if target.suffix == '.js':
                content_type = 'application/javascript; charset=utf-8'
            elif target.suffix == '.css':
                content_type = 'text/css; charset=utf-8'
            elif target.suffix == '.html':
                content_type = 'text/html; charset=utf-8'

            data = target.read_bytes()
            compressible = target.suffix in ('.js', '.css', '.html', '.json', '.svg') and len(data) > 1024
            gz = gzip.compress(data, compresslevel=6) if compressible else None
            cache_ctrl = 'public, max-age=31536000, immutable' if '/assets/' in path else 'no-cache'
            return self._send_bytes(200, data, gz, content_type=content_type, cache_control=cache_ctrl)
        finally:
            VISITOR_SESSION.reset(token)

    def do_POST(self):
        token = VISITOR_SESSION.set(self._extract_visitor_id())
        acquired = False
        try:
            if self.path == '/api/agent':
                acquired = AGENT_SEMAPHORE.acquire(blocking=False)
                if not acquired:
                    return self.send(429, {'error': '当前在线求证请求较多，请稍候几秒再试。'})
            if 'Origin' in self.headers:
                del self.headers['Origin']
            return super().do_POST()
        finally:
            if acquired:
                AGENT_SEMAPHORE.release()
            VISITOR_SESSION.reset(token)


def main():
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '7860'))
    print('Pre-warming Gzip caches for fast public cloud delivery...', flush=True)
    warmup_caches()
    print(f'SwingAudit CS2 Cloud Server listening on http://{host}:{port} (static root: {STATIC_ROOT})', flush=True)
    ThreadingHTTPServer((host, port), CloudHandler).serve_forever()


if __name__ == '__main__':
    main()
