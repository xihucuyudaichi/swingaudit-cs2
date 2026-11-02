"""Lab model client. Reads an existing credential assignment without running its script."""
import ast
import json
import os
import socket
import logging
import time
import random
import math
from email.utils import parsedate_to_datetime
from agent_policy import read_policy
import urllib.error
import urllib.request
from pathlib import Path
from provider import ProviderError, ProviderNotConfigured

MODEL = 'qwen3.8-27b'
MODEL_LABEL = '实验室 Qwen3.8 27B'
DEFAULT_CONFIG=Path(__file__).with_name('lab.local.json')

def read_config():
    path=Path(os.environ.get('ROUND_LAB_CONFIG',str(DEFAULT_CONFIG)))
    try:
        config=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(config,dict):raise ValueError()
        source=Path(config['credential_source'])
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        key=None
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='API_KEY' for t in node.targets):
                key=ast.literal_eval(node.value)
        if not isinstance(key,str) or not key.strip():raise ValueError()
        return {**config,'api_key':key.strip()}
    except (OSError,ValueError,KeyError,SyntaxError):
        raise ProviderNotConfigured(f'无法读取实验室模型配置或凭据，请检查 {path} 及 credential_source。') from None

def provider_status():
    try:read_config();configured,state=True,'configured_unverified'
    except ProviderNotConfigured:configured,state=False,'configuration_error'
    return {'model':MODEL,'model_label':MODEL_LABEL,'configured':configured,'provider_status':state,'provider':'lab'}

def _http_error(status, detail):
    context_error = status == 400 and any(x in detail for x in ('context length', 'context_length', 'input_tokens', 'too many tokens'))
    logging.warning('Model request rejected: status=%s category=%s', status, 'context_limit' if context_error else 'request_rejected')
    if context_error: hint = '检索数据超出模型可处理的范围，请指定选手或赛事后重试。'
    elif status == 400: hint = '模型服务未能接受本次分析请求，请重新提交；若持续出现，请检查模型接口配置。'
    elif status in (401, 403): hint = '模型服务认证失败，请检查账户权限或凭据配置。'
    elif status == 429: hint = '模型服务繁忙或请求额度不足，请稍后重试。'
    else: hint = '模型服务暂时不可用，请稍后重试。'
    return ProviderError(f'{hint}（HTTP {status}）')


def retry_delay(header, attempt, policy):
    """Respect a server wait hint; do not retry sooner than a long Retry-After."""
    delay = None
    if header:
        try: delay = float(header)
        except (TypeError, ValueError):
            try: delay = parsedate_to_datetime(header).timestamp() - time.time()
            except (TypeError, ValueError, OverflowError): pass
    if delay is None or not math.isfinite(delay):
        delay = policy['retry_base_seconds'] * (2 ** attempt) * random.uniform(1, 1.25)
    return max(0, delay)


def request_chat(messages, tools=None, require_tool=False, timeout_seconds=None, force_text=False, policy=None):
    policy = policy or read_policy()
    config = read_config()
    base, timeout, budget = config.get('base_url'), config.get('timeout_seconds',60), config.get('max_tokens',8192)
    if not isinstance(base,str) or not base.startswith(('https://','http://')): raise ProviderNotConfigured('实验室 base_url 配置无效。')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 1<=timeout<=180: raise ProviderNotConfigured('timeout_seconds 需在1–180之间。')
    if isinstance(budget,bool) or not isinstance(budget,int) or not 256<=budget<=65536: raise ProviderNotConfigured('max_tokens 需在256–65536之间。')
    if timeout_seconds is not None: timeout = min(timeout, timeout_seconds)
    if timeout <= 0: raise ProviderError('实验室模型请求超时，请重试。')
    deadline = time.monotonic() + timeout
    payload = {'model': MODEL, 'messages': messages, 'stream': False, 'max_tokens': budget,
               'temperature': policy['temperature'], 'chat_template_kwargs': {'enable_thinking': policy['enable_thinking']}}
    if tools:
        payload['tools'] = [{'type':'function','function':{k:v for k,v in t.items() if k in ('name','description','parameters')}} for t in tools]
        payload['tool_choice'] = 'none' if force_text else ('required' if require_tool else 'auto')
    req = urllib.request.Request(base.rstrip('/')+'/chat/completions', data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8'), headers={'Authorization':'Bearer '+config['api_key'],'Content-Type':'application/json','Accept':'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    attempts = 0
    for attempt in range(policy['http_max_retries'] + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0: raise ProviderError('实验室模型请求超时，请重试。')
        attempts += 1
        retryable, hint = False, None
        try:
            with opener.open(req, timeout=remaining) as response: result = json.load(response)
            break
        except urllib.error.HTTPError as error:
            status = error.code
            hint = error.headers.get('Retry-After') if error.headers else None
            try: detail = error.read(8192).decode('utf-8', errors='replace').lower()
            except (OSError, ValueError): detail = ''
            finally: error.close()
            failure = _http_error(status, detail)
            retryable = status in (408, 429, 500, 502, 503, 504)
        except (TimeoutError, socket.timeout):
            failure = ProviderError('实验室模型请求超时，请重试。')
            retryable = True
        except (urllib.error.URLError, OSError):
            failure = ProviderError('无法连接实验室模型服务，请检查网络。')
            retryable = True
        except ValueError:
            raise ProviderError('实验室模型返回了无效的JSON。') from None
        delay = retry_delay(hint, attempt, policy)
        if not retryable or attempt >= policy['http_max_retries'] or delay > policy['retry_max_delay_seconds'] or deadline - time.monotonic() <= delay + 1:
            raise failure from None
        logging.info('Retrying model request: attempt=%s', attempts + 1)
        time.sleep(delay)
    choices = result.get('choices') if isinstance(result,dict) else None
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict): raise ProviderError('实验室模型未返回有效回答。')
    if choices[0].get('finish_reason') == 'length': raise ProviderError('本次分析内容过长，未能完整生成。请缩小问题范围后重试。')
    if choices[0].get('finish_reason') == 'content_filter': raise ProviderError('模型服务未能回答此问题，请换一种表述后重试。')
    message = choices[0].get('message')
    if not isinstance(message,dict): raise ProviderError('实验室模型回答格式无效。')
    return {**{k:message[k] for k in ('role','content','tool_calls') if k in message}, '_telemetry': {'http_attempts': attempts}}
