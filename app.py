"""Root entrypoint for ModelScope Studio / Hugging Face Spaces / Docker (0.0.0.0:7860)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def ensure_frontend_dist():
    dist_index = ROOT / 'dist' / 'index.html'
    fallback_index = ROOT / '.planning/2026-11-02-sites-deploy/public-dist/index.html'
    if dist_index.is_file() or fallback_index.is_file():
        return
    npm_bin = shutil.which('npm')
    if npm_bin and (ROOT / 'package.json').is_file():
        print('Building frontend static assets (dist/)...', flush=True)
        subprocess.run([npm_bin, 'ci', '--registry=https://registry.npmmirror.com'], cwd=ROOT, check=True)
        subprocess.run([npm_bin, 'run', 'build'], cwd=ROOT, check=True)


if __name__ == '__main__':
    ensure_frontend_dist()
    import cloud_server
    cloud_server.main()
