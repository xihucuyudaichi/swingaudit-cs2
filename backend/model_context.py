"""Bound model input independently of the full, user-visible evidence trace."""
import json

MAX_HISTORY_BYTES = 60000
MAX_TOOL_BYTES = 12000
PRIORITY = ('missing', 'reason', 'year', 'query', 'total_matches', 'name', 'id', 'rank', 'official_rank',
            'rating_estimate', 'weighted_honor_score', 'maps', 'mvp', 'evp', 'source', 'sources',
            'source_file', 'source_url', 'sheet', 'row', 'evidence', 'notice', 'limitations',
            'results', 'players', 'comparison_note', 'same_tactical_niche', 'player_attributions',
            'rankings', 'hybrid_rankings', 'multi_tier_benchmarks', 'peer_benchmarks', 'style_metrics')


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def size(value):
    return len(encode(value).encode('utf-8'))


def summarize_tool(value, budget=MAX_TOOL_BYTES):
    if size(value) <= budget:
        return encode(value)
    for limit in (20, 8, 4, 2, 1):
        omitted = []
        def compact(node, path='$', depth=0):
            if isinstance(node, dict):
                keys = sorted(node, key=lambda k: (PRIORITY.index(k) if k in PRIORITY else len(PRIORITY)))
                keep = keys[:max(12, limit * 3)]
                if len(keep) < len(keys): omitted.append(path + ' (fields)')
                return {k: compact(node[k], path + '.' + k, depth+1) for k in keep}
            if isinstance(node, list):
                if len(node) > limit: omitted.append(path + ' (items)')
                return [compact(v, path + '[]', depth+1) for v in node[:limit]]
            if isinstance(node, str) and len(node.encode('utf-8')) > max(512, budget // 4):
                omitted.append(path + ' (long text)')
                return {'omitted': True, 'reason': 'Long text retained in full evidence trace'}
            return node
        summary = compact(value)
        packed = {'data': summary, '_context_summary': {
            'partial': True,
            'omitted_sections': omitted[:12],
            'notice': '仅供回答的证据摘要；完整数据保留在来源记录中。列表可能不完整，不得据此统计总数或断言未列出的数据不存在。'}}
        if size(packed) <= budget:
            return encode(packed)
    # No invalid JSON slices or invented numbers if a deeply nested result still exceeds its share.
    return encode({'_context_summary': {'partial': True, 'omitted': True,
        'notice': '本项完整记录过大，已保留在来源记录中。请按具体选手或赛事重新查询，不得臆测其内容。'}})


def prepare_history(history, max_history_bytes=MAX_HISTORY_BYTES, max_tool_bytes=MAX_TOOL_BYTES):
    tool_messages = [m for m in history if m.get('role') == 'tool']
    if not tool_messages:
        if size(history) > max_history_bytes:
            raise ValueError('分析上下文过长，请缩小问题范围后重试。')
        return history
    non_tool_bytes = size([m for m in history if m.get('role') != 'tool'])
    overhead = sum(size({k:v for k,v in m.items() if k != 'content'}) for m in tool_messages)
    # Quoted JSON strings need extra escaping in the outer message envelope.
    budget = min(max_tool_bytes, (max_history_bytes - non_tool_bytes - overhead - 2048) // (2 * len(tool_messages)))
    if budget < 512:
        raise ValueError('分析上下文过长，请缩小问题范围后重试。')
    for _ in range(8):
        prepared = [{**m, 'content': summarize_tool(json.loads(m['content']), budget)}
                    if m.get('role') == 'tool' else dict(m) for m in history]
        if size(prepared) <= max_history_bytes:
            return prepared
        budget //= 2
        if budget < 512: break
    raise ValueError('分析上下文过长，请缩小问题范围后重试。')
