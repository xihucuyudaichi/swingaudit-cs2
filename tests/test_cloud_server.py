from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import gzip
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import cloud_server


class CloudServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cloud_server.warmup_caches()
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), cloud_server.CloudHandler)
        cls.port = cls.httpd.server_address[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_gzip_bootstrap_and_static_root(self):
        # 1. Static HTML index
        req_html = urllib.request.Request(self.base + '/', headers={'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req_html, timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertIn('text/html', res.headers.get('Content-Type', ''))
            self.assertEqual(res.headers.get('Cache-Control'), 'no-cache')

        # 1b. Static WebP image caching & ETag 304 support
        index = (cloud_server.STATIC_ROOT / 'index.html').read_text(encoding='utf-8')
        image_path = '/' + re.search(r'href="(?:\./|/)(atlas-arch\.[0-9a-f]{12}\.webp)"', index).group(1)
        req_webp = urllib.request.Request(self.base + image_path)
        with urllib.request.urlopen(req_webp, timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertIn('max-age=31536000', res.headers.get('Cache-Control', ''))
            self.assertIn('immutable', res.headers.get('Cache-Control', ''))
            self.assertEqual(res.headers.get('Content-Type'), 'image/webp')
            etag = res.headers.get('ETag')
            self.assertTrue(etag)
            webp_bytes = res.read()
            self.assertLess(len(webp_bytes), 500 * 1024)

        for validator in (etag, etag.removeprefix('W/'), '"old", ' + etag, '*'):
            req_304 = urllib.request.Request(self.base + image_path, headers={'If-None-Match': validator})
            with self.assertRaises(urllib.error.HTTPError) as result:
                urllib.request.urlopen(req_304, timeout=10)
            err = result.exception
            self.assertEqual(err.code, 304)
            self.assertEqual(err.headers.get('Vary'), 'Accept-Encoding')
            self.assertEqual(err.headers.get('ETag'), etag)
            self.assertEqual(err.read(), b'')
            err.close()

        with urllib.request.urlopen(urllib.request.Request(self.base + image_path,
                headers={'If-None-Match': '"old"'}), timeout=10) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.read(), webp_bytes)

        # 2. Gzipped /api/bootstrap
        req_boot = urllib.request.Request(self.base + '/api/bootstrap', headers={'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(req_boot, timeout=15) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.headers.get('Content-Encoding'), 'gzip')
            compressed = res.read()
            # Compressed bootstrap must be < 15 MB (vs ~87 MB raw)
            self.assertLess(len(compressed), 15 * 1024 * 1024)
            data = json.loads(gzip.decompress(compressed).decode('utf-8'))
            self.assertIn('2025', data['data']['seasons'])
            self.assertIn('2026', data['data']['seasons'])

    def test_static_cache_refreshes_changed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'index.html'
            file.write_bytes(b'a' * 2048)
            original = cloud_server._get_cached_static_file(file, '/')
            self.assertEqual(gzip.decompress(original[1]), original[0])
            self.assertEqual(original[3], 'no-cache')
            file.write_bytes(b'b' * 3072)
            updated = cloud_server._get_cached_static_file(file, '/')
            self.assertEqual(updated[0], b'b' * 3072)
            self.assertNotEqual(updated[4], original[4])
            self.assertEqual(gzip.decompress(updated[1]), updated[0])
            cloud_server.STATIC_FILE_CACHE.pop(str(file), None)

    def test_cross_origin_post_and_visitor_isolation(self):
        # Simulate ModelScope Studio *.ms.show Origin header on POST /api/compare and /api/records
        compare_body = json.dumps({'year': '2025', 'players': ['donk', 'zywoo'], 'metric': 'overall'}).encode('utf-8')
        req_cmp = urllib.request.Request(
            self.base + '/api/compare',
            data=compare_body,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://xihucuyudaichi-swingaudit-cs2.ms.show',
            },
            method='POST',
        )
        with urllib.request.urlopen(req_cmp, timeout=10) as res:
            self.assertEqual(res.status, 200)
            payload = json.loads(res.read().decode('utf-8'))
            self.assertEqual(payload['year'], '2025')

        # Visitor A saves a record; Visitor B does not see Visitor A's private record
        rec_body = json.dumps({'title': 'Cloud test note', 'payload': {'year': '2025'}}).encode('utf-8')
        req_save = urllib.request.Request(
            self.base + '/api/records',
            data=rec_body,
            headers={
                'Content-Type': 'application/json',
                'Origin': 'https://xihucuyudaichi-swingaudit-cs2.ms.show',
                'X-Demo-Session': 'visitor_alpha_1234',
            },
            method='POST',
        )
        with urllib.request.urlopen(req_save, timeout=10) as res:
            self.assertEqual(res.status, 200)

        req_get_b = urllib.request.Request(
            self.base + '/api/records',
            headers={'X-Demo-Session': 'visitor_beta_5678'},
        )
        with urllib.request.urlopen(req_get_b, timeout=10) as res:
            records_b = json.loads(res.read().decode('utf-8'))['records']
            self.assertEqual(records_b, [])



    def test_env_secret_injection_into_lab_provider(self):
        old_base = os.environ.get('ROUND_LAB_BASE_URL')
        old_key = os.environ.get('ROUND_LAB_API_KEY')
        try:
            os.environ['ROUND_LAB_BASE_URL'] = 'http://198.51.100.10:30938/v1'
            os.environ['ROUND_LAB_API_KEY'] = 'test_secret_token_only'
            cfg = cloud_server.lab_provider.read_config()
            self.assertEqual(cfg['base_url'], 'http://198.51.100.10:30938/v1')
            self.assertEqual(cfg['api_key'], 'test_secret_token_only')
        finally:
            if old_base is None:
                os.environ.pop('ROUND_LAB_BASE_URL', None)
            else:
                os.environ['ROUND_LAB_BASE_URL'] = old_base
            if old_key is None:
                os.environ.pop('ROUND_LAB_API_KEY', None)
            else:
                os.environ['ROUND_LAB_API_KEY'] = old_key


if __name__ == '__main__':
    unittest.main()
