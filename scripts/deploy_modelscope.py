"""One-command deployment script for ModelScope Studio (Docker mode, 2vCPU 16GB RAM free).

Usage:
  $env:MODELSCOPE_API_KEY="your_modelscope_sdk_token"
  python scripts/deploy_modelscope.py

Or:
  python scripts/deploy_modelscope.py --token "your_modelscope_sdk_token"
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = os.environ.get('MODELSCOPE_ENDPOINT', 'https://modelscope.cn').rstrip('/')
API_BASE = f'{ENDPOINT}/openapi/v1'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api_call(method: str, path: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f'{API_BASE}{path}'
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'User-Agent': 'SwingAudit-CS2-Deployer/1.0',
    }
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            return resp.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', errors='replace')
        try:
            body = json.loads(raw)
        except ValueError:
            body = {'message': raw}
        return e.code, body


def read_local_lab_credentials() -> dict[str, str]:
    """Read local backend/lab.local.json and credentials.local.py without printing secrets."""
    cfg_path = ROOT / 'backend/lab.local.json'
    if not cfg_path.is_file():
        return {}
    try:
        cfg = json.loads(cfg_path.read_text(encoding='utf-8-sig'))
        base_url = str(cfg.get('base_url') or '').strip()
        cred_src = Path(cfg.get('credential_source') or '')
        if not cred_src.is_absolute():
            cred_src = ROOT / cred_src
        if not cred_src.is_file():
            return {}
        tree = ast.parse(cred_src.read_text(encoding='utf-8-sig'))
        api_key = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'API_KEY' for t in node.targets
            ):
                api_key = ast.literal_eval(node.value)
        if not base_url or not isinstance(api_key, str) or not api_key.strip():
            return {}
        return {
            'ROUND_LAB_BASE_URL': base_url,
            'ROUND_LAB_API_KEY': api_key.strip(),
            'ROUND_LAB_TIMEOUT_SECONDS': str(cfg.get('timeout_seconds', 60)),
            'ROUND_LAB_MAX_TOKENS': str(cfg.get('max_tokens', 8192)),
        }
    except Exception:
        return {}


def upsert_secret(owner: str, repo: str, token: str, key: str, value: str):
    status, data = api_call('GET', f'/studios/{owner}/{repo}/secrets', token)
    existing = set()
    if status == 200 and isinstance(data.get('data'), list):
        for item in data['data']:
            if isinstance(item, dict) and item.get('key'):
                existing.add(item['key'])
    elif status == 200 and isinstance(data.get('data'), dict):
        for item in data['data'].get('secrets') or data['data'].get('items') or []:
            if isinstance(item, dict) and item.get('key'):
                existing.add(item['key'])

    method = 'PUT' if key in existing else 'POST'
    st, res = api_call(method, f'/studios/{owner}/{repo}/secrets', token, {'key': key, 'value': value})
    if st not in (200, 201) or res.get('success') is False:
        # Try the opposite method in case list structure differed
        alt = 'POST' if method == 'PUT' else 'PUT'
        st, res = api_call(alt, f'/studios/{owner}/{repo}/secrets', token, {'key': key, 'value': value})
    print(f'  -> Secret [{key}] synced (HTTP {st})')


def sync_git_to_modelscope(owner: str, repo: str, token: str):
    host = ENDPOINT.replace('https://', '').replace('http://', '')
    remote_url = f'https://oauth2:{token}@{host}/studios/{owner}/{repo}.git'
    subprocess.run(['git', 'config', 'http.postBuffer', '524288000'], cwd=ROOT, check=False)
    subprocess.run(['git', 'lfs', 'install'], cwd=ROOT, check=False)

    current_branch = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT, text=True
    ).strip()

    temp_branch = 'ms-studio-sync-temp'
    try:
        subprocess.run(['git', 'branch', '-D', temp_branch], cwd=ROOT, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', temp_branch], cwd=ROOT, check=True)
        subprocess.run(['git', 'remote', 'remove', 'modelscope'], cwd=ROOT, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'modelscope', remote_url], cwd=ROOT, check=True)

        print('Fetching remote ModelScope Studio master branch...')
        fetch_res = subprocess.run(['git', 'fetch', 'modelscope', 'master'], cwd=ROOT, capture_output=True, text=True)
        if fetch_res.returncode == 0:
            merge_res = subprocess.run(
                [
                    'git', 'merge', 'modelscope/master',
                    '--allow-unrelated-histories', '-X', 'ours',
                    '-m', 'Merge ModelScope Studio initial master',
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if merge_res.returncode != 0:
                subprocess.run(['git', 'checkout', '--ours', '.'], cwd=ROOT, check=False)
                subprocess.run(['git', 'add', '.'], cwd=ROOT, check=False)
                subprocess.run(['git', 'commit', '-m', 'Resolve merge keeping local snapshot'], cwd=ROOT, check=False)

        print('Pushing repository to ModelScope Studio (master)...')
        push_res = subprocess.run(
            ['git', 'push', '-u', 'modelscope', f'{temp_branch}:master'],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if push_res.returncode != 0:
            err_msg = (push_res.stderr or push_res.stdout or '').replace(token, '***')
            if 'exceeds file size limit' in err_msg or 'LFS' in err_msg or '413' in err_msg:
                print('Remote requested Git LFS for large data files; migrating data/historical.json on deploy branch...')
                subprocess.run(['git', 'lfs', 'track', 'data/historical.json'], cwd=ROOT, check=True)
                subprocess.run(['git', 'add', '.gitattributes', 'data/historical.json'], cwd=ROOT, check=True)
                subprocess.run(['git', 'commit', '-m', 'Track historical.json via Git LFS for Studio'], cwd=ROOT, check=True)
                push_res2 = subprocess.run(
                    ['git', 'push', '-u', 'modelscope', f'{temp_branch}:master'],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                if push_res2.returncode != 0:
                    raise RuntimeError('Git push failed: ' + (push_res2.stderr or '').replace(token, '***'))
            else:
                raise RuntimeError('Git push failed: ' + err_msg)
        print('Git push to ModelScope Studio master succeeded!')
    finally:
        # Remove token-bearing remote URL and restore original branch
        subprocess.run(['git', 'remote', 'remove', 'modelscope'], cwd=ROOT, capture_output=True)
        subprocess.run(['git', 'checkout', current_branch], cwd=ROOT, capture_output=True)
        subprocess.run(['git', 'branch', '-D', temp_branch], cwd=ROOT, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description='Deploy SwingAudit CS2 to ModelScope Studio (Docker mode)')
    parser.add_argument('--token', default=os.environ.get('MODELSCOPE_API_KEY', ''), help='ModelScope Access Token')
    parser.add_argument('--repo', default='swingaudit-cs2', help='Studio English name (default: swingaudit-cs2)')
    parser.add_argument('--owner', default='', help='ModelScope username (auto-detected if omitted)')
    args = parser.parse_args()

    token = args.token.strip()
    if not token:
        print('ERROR: Missing ModelScope Access Token.')
        print('1. Visit https://modelscope.cn/my/myaccesstoken to copy your SDK Token.')
        print('2. Run: python scripts/deploy_modelscope.py --token "<YOUR_TOKEN>"')
        sys.exit(1)

    owner = args.owner.strip()
    if not owner:
        st, me = api_call('GET', '/users/me', token)
        if st != 200 or not me.get('data'):
            print(f'ERROR: Failed to authenticate token via /users/me (HTTP {st}): {me}')
            sys.exit(1)
        user_data = me['data']
        owner = user_data.get('username') or user_data.get('Name') or user_data.get('name') or ''
        if not owner:
            print(f'ERROR: Could not parse username from /users/me response: {me}')
            sys.exit(1)

    repo = args.repo.strip()
    print(f'Authenticated as ModelScope user: {owner} | Target Studio: {owner}/{repo}')

    # Query available free hardware dynamically
    free_hw = 'platform/2v-cpu-8g-mem'
    st_hw, hw_res = api_call('GET', '/studios/hardware?sdk_type=docker', token)
    if st_hw == 200 and isinstance(hw_res.get('data'), dict):
        for item in hw_res['data'].get('hardware') or []:
            if isinstance(item, dict) and item.get('resource_type') == 'free' and item.get('name'):
                free_hw = item['name']
                break
    print(f'Selected free hardware spec: {free_hw}')

    # Check if Studio exists
    st, info = api_call('GET', f'/studios/{owner}/{repo}', token)
    if st != 200 or info.get('success') is False:
        print(f'Creating new Docker Studio {owner}/{repo} (2vCPU 16GB RAM Free)...')
        create_payload = {
            'owner': owner,
            'repo_name': repo,
            'sdk_type': 'docker',
            'visibility': 'public',
            'hardware': free_hw,
            'display_name': 'SwingAudit · CS2 选手观察室',
            'chinese_name': 'SwingAudit · CS2 选手观察室',
            'description': '浙江大学《设计大数据基础》课程项目：面向 CS/CS2 职业选手的多源证据检索、同位置比较、年度排名分析与未来赛事条件推演。',
        }
        cst, cres = api_call('POST', '/studios', token, create_payload)
        if cst not in (200, 201) or cres.get('success') is False:
            print(f'ERROR creating Docker Studio (HTTP {cst}): {cres}')
            print('Note: ModelScope Docker Studios require real-name verification & Aliyun account binding: https://modelscope.cn/docs/studios/docker')
            sys.exit(1)
        print('Studio created successfully!')
    else:
        print(f'Studio {owner}/{repo} already exists. Ensuring public visibility & Docker SDK...')
        api_call(
            'PATCH',
            f'/studios/{owner}/{repo}/settings',
            token,
            {'sdk_type': 'docker', 'hardware': free_hw, 'visibility': 'public'},
        )

    # Sync code via Git
    sync_git_to_modelscope(owner, repo, token)

    # Sync local lab model credentials into encrypted Secrets
    secrets = read_local_lab_credentials()
    if secrets:
        print('Syncing local lab model configuration to ModelScope encrypted Secrets...')
        for k, v in secrets.items():
            upsert_secret(owner, repo, token, k, v)
    else:
        print('Note: No local backend/lab.local.json found; skipping Secret sync.')

    # Trigger deployment
    print('Triggering Studio build & deployment...')
    dst, dres = api_call('POST', f'/studios/{owner}/{repo}/deploy', token)
    print(f'Deploy trigger response (HTTP {dst}): {dres.get("success", True)}')

    studio_url = f'{ENDPOINT}/studios/{owner}/{repo}'
    direct_host = f'{owner}-{repo}'.lower().replace('_', '-')
    direct_url = f'https://{direct_host}.ms.show'
    print('\n============================================================')
    print(f'ModelScope Studio Page : {studio_url}')
    print(f'Standalone Direct Demo : {direct_url}')
    print('============================================================')


if __name__ == '__main__':
    main()
