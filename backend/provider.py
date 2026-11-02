"""Server-only Agnes 3.0 Flash client; reads local config on every request."""
import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path

MODEL = 'agnes-3.0-flash'
MODEL_LABEL = 'Agnes 3.0 Flash'
DEFAULT_CONFIG = Path(__file__).with_name('agnes.local.json')

class ProviderNotConfigured(RuntimeError):
    pass

class ProviderError(RuntimeError):
    pass

def read_config():
    path = Path(os.environ.get('ROUND_AGNES_CONFIG', str(DEFAULT_CONFIG)))
    try:
        config = json.loads(path.read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        raise ProviderNotConfigured(f'请创建 {path} 并填写 api_key。') from None
    except (ValueError, OSError):
        raise ProviderNotConfigured(f'无法读取 Agnes 配置，请检查 {path} 的 JSON 格式。') from None
    if not isinstance(config, dict):
        raise ProviderNotConfigured('Agnes 配置必须为 JSON 对象。')
    return config

def provider_status():
    try:
        key = read_config().get('api_key', '')
        configured = isinstance(key, str) and bool(key.strip())
        state = 'configured_unverified' if configured else 'missing_api_key'
    except ProviderNotConfigured:
        configured, state = False, 'configuration_error'
    return {'model': MODEL, 'model_label': MODEL_LABEL, 'configured': configured, 'provider_status': state}

def request_chat(messages, tools=None, require_tool=False, timeout_seconds=None, force_text=False, policy=None):
    config = read_config()
    key = config.get('api_key', '')
    if not isinstance(key, str) or not key.strip():
        path = Path(os.environ.get('ROUND_AGNES_CONFIG', str(DEFAULT_CONFIG)))
        raise ProviderNotConfigured(f'Agnes API Key 尚未填写，请在 {path} 的 api_key 字段中填写；保存后可直接重试。')
    base = config.get('base_url', 'https://apihub.agnes-ai.com/v1')
    if not isinstance(base, str) or not base.startswith(('https://','http://127.0.0.1:')):
        raise ProviderNotConfigured('Agnes base_url 配置无效。')
    timeout, budget = config.get('timeout_seconds',60), config.get('max_tokens',2048)
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 1<=timeout<=180:
        raise ProviderNotConfigured('timeout_seconds 需在1–180之间。')
    if isinstance(budget,bool) or not isinstance(budget,int) or not 256<=budget<=65536:
        raise ProviderNotConfigured('max_tokens 需在256–65536之间。')
    if timeout_seconds is not None:
        timeout = min(timeout, max(0.1, timeout_seconds))
    payload = {'model':MODEL,'messages':messages,'stream':False,'max_tokens':budget,
               'chat_template_kwargs':{'enable_thinking':False}}
    if tools:
        payload['tools'] = [{'type':'function','function':{k:v for k,v in t.items() if k in ('name','description','parameters')}} for t in tools]
        payload['tool_choice'] = 'none' if force_text else ('required' if require_tool else 'auto')
    req = urllib.request.Request(base.rstrip('/')+'/chat/completions',
        data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8'),
        headers={'Authorization':'Bearer '+key.strip(),'Content-Type':'application/json','Accept':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as e:
        status = e.code
        e.close()
        hint = '请检查 API Key 与账户权限。' if status in (401,403) else '请稍后重试或检查账户限额。' if status==429 else '请稍后重试。'
        raise ProviderError(f'Agnes 服务返回 HTTP {status}，{hint}') from None
    except (TimeoutError, socket.timeout):
        raise ProviderError('Agnes 请求超时，请稍后重试。') from None
    except (urllib.error.URLError, OSError):
        raise ProviderError('无法连接 Agnes 服务，请检查网络后重试。') from None
    except ValueError:
        raise ProviderError('Agnes 返回了无效的 JSON 响应。') from None
    choices = result.get('choices') if isinstance(result,dict) else None
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):
        raise ProviderError('Agnes 未返回有效的回答。')
    if choices[0].get('finish_reason') in ('length','content_filter'):
        raise ProviderError('Agnes 回答未完整生成，请缩短问题或调整 max_tokens 后重试。')
    message = choices[0].get('message')
    if not isinstance(message,dict):
        raise ProviderError('Agnes 回答格式无效。')
    return {k:message[k] for k in ('role','content','tool_calls') if k in message}

if __name__ == '__main__':
    print(json.dumps(provider_status(), ensure_ascii=False))
