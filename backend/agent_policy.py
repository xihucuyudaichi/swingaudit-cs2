"""Validated, credential-free execution policy. Read once at the start of each run."""
import json
import math
import os
from pathlib import Path
from provider import ProviderNotConfigured

DEFAULT_PATH = Path(__file__).with_name('agent_policy.json')
BOUNDS = {
    'max_model_turns': (int, 2, 8), 'max_tools_per_turn': (int, 1, 8),
    'max_tool_executions': (int, 1, 24), 'max_validation_repairs': (int, 0, 2),
    'run_timeout_seconds': (int, 10, 110), 'max_history_bytes': (int, 8000, 60000),
    'max_tool_bytes': (int, 1024, 12000), 'http_max_retries': (int, 0, 2),
    'retry_base_seconds': (float, 0.05, 2), 'retry_max_delay_seconds': (float, 0.1, 5),
    'temperature': (float, 0, 1),
}

def read_policy():
    path = Path(os.environ.get('ROUND_AGENT_POLICY', str(DEFAULT_PATH)))
    try:
        policy = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(policy, dict) or set(policy) != set(BOUNDS) | {'enable_thinking'}:
            raise ValueError()
        for key, (kind, low, high) in BOUNDS.items():
            value = policy[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value): raise ValueError()
            if kind is int and not isinstance(value, int): raise ValueError()
            if not low <= value <= high: raise ValueError()
        if not isinstance(policy['enable_thinking'], bool): raise ValueError()
        if policy['max_tool_bytes'] > policy['max_history_bytes'] or policy['retry_base_seconds'] > policy['retry_max_delay_seconds']: raise ValueError()
        return policy
    except (OSError, ValueError, KeyError):
        raise ProviderNotConfigured('Agent执行策略配置无效，请检查 agent_policy.json 的字段与取值。') from None
