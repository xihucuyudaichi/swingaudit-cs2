"""Validated, bounded, per-run execution of read-only research tools."""
import json
import time
from jsonschema import Draft202012Validator
from provider import ProviderError

class ToolSession:
    def __init__(self, tools, execute, policy, deadline):
        self.validators = {t['name']: Draft202012Validator(t['parameters']) for t in tools}
        self.execute, self.policy, self.deadline = execute, policy, deadline
        self.cache = {}
        self.executions = self.cache_hits = self.errors = 0

    def call(self, name, raw_args, allow_execute=True):
        if not isinstance(name, str) or name not in self.validators:
            self.errors += 1
            return None, {'not_executed': True, 'error': 'unknown_tool', 'hint': '请使用已提供的工具名称。'}, False
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            # Reject non-JSON numbers before schema validation, including nested values.
            json.dumps(args, allow_nan=False)
            errors = list(self.validators[name].iter_errors(args))
            if errors:
                fields = ['.'.join(str(x) for x in e.absolute_path) or '$' for e in errors[:4]]
                raise ValueError('请按工具参数定义修正字段：' + ', '.join(fields))
        except (ValueError, TypeError, RecursionError):
            self.errors += 1
            return None, {'not_executed': True, 'error': 'invalid_arguments', 'hint': '参数必须为符合工具schema的JSON对象，核对必填字段、类型、年份与额外字段后重试。'}, False
        key = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
        if key in self.cache:
            self.cache_hits += 1
            return args, self.cache[key], False
        if not allow_execute or self.executions >= self.policy['max_tool_executions']:
            return args, {'not_executed': True, 'error': 'tool_budget', 'hint': '本轮或本次查询额度已用完，请使用已有证据总结；未执行的查询不代表数据缺失。'}, False
        if time.monotonic() >= self.deadline:
            raise ProviderError('分析等待超时，请缩小问题范围后重试。')
        self.executions += 1
        try:
            result = self.execute(name, args)
        except (ValueError, KeyError, TypeError):
            self.errors += 1
            return args, {'not_executed': True, 'error': 'tool_input_rejected', 'hint': '查询条件无法执行，请修正工具参数或使用其他已提供的查询工具。'}, False
        self.cache[key] = result
        return args, result, True
