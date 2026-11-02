"""Append-only, deterministic future-event assumptions; never rewrite results."""
import copy
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from knowledge import load_event_weights
from train_model import fit_and_predict_hybrid

ROOT = Path(__file__).resolve().parents[1]


def today_shanghai():
    return datetime.now(timezone(timedelta(hours=8))).date()


def upcoming_catalog(today=None):
    today = today or today_shanghai()
    catalog = json.loads((ROOT / 'data/upcoming_events.json').read_text(encoding='utf-8'))
    return {**catalog, 'as_of': today.isoformat(), 'events': [
        e for e in catalog['events'] if e['start_date'] > today.isoformat()
    ], 'tiers': list(load_event_weights()['tier_weights'])}


def _number(value, label, lo, hi, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not lo <= value <= hi
            or (integer and value != int(value))):
        raise ValueError(f'{label}须为{lo}–{hi}之间的' + ('整数。' if integer else '数值。'))
    return int(value) if integer else float(value)


def _reaggregate(p):
    rows = [r for r in p['events'] if isinstance(r.get('rating'), (int, float)) and (r.get('maps') or 0) > 0]
    p['maps'] = sum(r['maps'] for r in rows)
    p['rating_estimate'] = round(sum(r['rating'] * r['maps'] for r in rows) / p['maps'], 4) if p['maps'] else None
    p['mvp'] = sum(r.get('award') == 'MVP' for r in rows)
    p['evp'] = sum(r.get('award') == 'EVP' for r in rows)


def simulate_future(data, body, today=None):
    today = today or today_shanghai()
    year = str(body.get('year', ''))
    if year != str(today.year):
        raise ValueError('If 线仅推演本年度尚未开赛的赛事；往年已结束，不能改写。')
    season = data['seasons'].get(year)
    if not season:
        raise ValueError('本年度尚无收录数据，无法建立年度比较基线。')
    cfg = load_event_weights()
    catalog = upcoming_catalog(today)
    all_catalog = json.loads((ROOT / 'data/upcoming_events.json').read_text(encoding='utf-8'))['events']
    known = {e['id']: e for e in all_catalog}
    historical_names = {e['name'].strip().casefold() for e in season['events']}
    items = body.get('events')
    if not isinstance(items, list) or not 1 <= len(items) <= 8:
        raise ValueError('请设置1–8站未来赛事。')

    # Only completed, dated records can enter the baseline. No future results leak in.
    base = copy.deepcopy(season['players'])
    excluded = 0
    for p in base:
        records = p.get('events', [])
        p['events'] = [r for r in records if r.get('period_end') and r['period_end'] < today.isoformat()]
        excluded += len(records) - len(p['events'])
        _reaggregate(p)
    base = [p for p in base if p['maps'] > 0]
    before_players = {p['id']: p for p in base}
    sandbox = copy.deepcopy(base)
    players = {p['id']: p for p in sandbox}
    manifest, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('赛事设定格式不正确。')
        if item.get('event_id') == 'custom':
            meta = {k: item.get(k) for k in ('name', 'start_date', 'end_date', 'tier')}
            meta.update(id='custom', source_url=None)
            if any(str(meta['name']).strip().casefold() == e['name'].casefold() for e in all_catalog):
                raise ValueError('已收录的未来赛事请从赛程选择，不能另建同名赛事。')
        else:
            meta = copy.deepcopy(known.get(item.get('event_id')))
            if not meta:
                raise ValueError('未找到未来赛事，请刷新赛程或使用自定义赛事。')
        name = meta.get('name')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
            raise ValueError('请填写1–100字的赛事名称。')
        name = name.strip()
        if name.casefold() in seen or name.casefold() in historical_names:
            raise ValueError('赛事重复或已存在历史成绩，不能重复累计或改写。')
        seen.add(name.casefold())
        try:
            start, end = date.fromisoformat(meta['start_date']), date.fromisoformat(meta['end_date'])
        except (ValueError, TypeError, KeyError):
            raise ValueError('请填写有效的开赛与结束日期。')
        if start <= today or end < start or start.year != int(year) or end.year != int(year):
            raise ValueError('赛事必须在今天之后开赛，并在本年度内结束。')
        tier = meta.get('tier')
        if tier not in cfg['tier_weights']:
            raise ValueError('不支持的赛事级别。')
        assumptions = item.get('players')
        if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 100:
            raise ValueError('每站请设置1–100位假设参赛选手。')
        mvp = item.get('mvp_player') or ''
        selected, records, team_places = set(), [], {}
        for a in assumptions:
            if not isinstance(a, dict):
                raise ValueError('选手设定格式不正确。')
            pid = a.get('player_id')
            if pid not in players or pid in selected:
                raise ValueError('选手缺少有效历史基线或在同一站重复。')
            selected.add(pid)
            rating = _number(a.get('rating'), 'Rating', 0, 3)
            maps = _number(a.get('maps'), '地图数', 1, 50, True)
            place = a.get('team_place', '未设定')
            if place not in [*cfg['placement_points'], '未设定']:
                raise ValueError('不支持的队伍成绩。')
            team = a.get('team', '').strip() if isinstance(a.get('team', ''), str) else ''
            if place != '未设定' and not team:
                raise ValueError('设定队伍成绩时请填写假设队名，以校验冠军唯一及同队成绩一致。')
            if len(team) > 60:
                raise ValueError('队名过长。')
            if team:
                key = team.casefold()
                if key in team_places and team_places[key] != place:
                    raise ValueError('同队选手的队伍成绩必须一致。')
                team_places[key] = place
            award = 'MVP' if pid == mvp else ('EVP' if a.get('evp') is True else '无')
            if award != '无' and maps < 3:
                raise ValueError('MVP / EVP 假设至少需要3张参赛地图。')
            records.append({'player_id': pid, 'name': players[pid]['name'], 'event': name,
                'rating': rating, 'maps': maps, 'team': team, 'team_place': place,
                'award': award, 'tier': tier, 'source_weight': cfg['tier_weights'][tier],
                'period_start': start.isoformat(), 'period_end': end.isoformat(),
                'provenance': 'user_assumption', 'source_file': 'future_scenario',
                'source_url': None, 'rating_version': 'hypothetical'})
        if mvp and mvp not in selected:
            raise ValueError('MVP 必须属于本次设定的参赛选手。')
        if list(team_places.values()).count('冠军') > 1 or list(team_places.values()).count('亚军') > 1:
            raise ValueError('同一站不能设置两个冠军队伍或两个亚军队伍。')
        for r in records:
            players[r['player_id']]['events'].append(r)
        manifest.append({**meta, 'name': name, 'players': records,
            'mvp_player': mvp, 'mvp_name': players[mvp]['name'] if mvp else '未设定',
            'participants_status': 'user_assumed', 'weight': cfg['tier_weights'][tier]})
    for p in sandbox:
        _reaggregate(p)
    train = [p for p in data['seasons'].get(str(today.year - 1), {}).get('players', [])
             if ((p.get('maps') or 0) >= 20 or p.get('official_rank')) and p.get('cohort_tier') != 'extended_pro']
    if not train:
        raise ValueError('缺少上一年度训练基线，无法计算综合分。')
    # Fixed training data and seed for both branches; unaffected player scores stay identical.
    b_rows = {r['id']: r for r in fit_and_predict_hybrid(train, base, cfg)['hybrid_rankings']}
    after = fit_and_predict_hybrid(train, sandbox, cfg)['hybrid_rankings']
    rows = []
    for r in after:
        b, bp, ap = b_rows[r['id']], before_players[r['id']], players[r['id']]
        rows.append({'id': r['id'], 'name': r['name'], 'before_rank': b['hybrid_rank'],
            'rank': r['hybrid_rank'], 'change': b['hybrid_rank'] - r['hybrid_rank'],
            'before': b['hybrid_score'], 'after': r['hybrid_score'],
            'score_delta': round(r['hybrid_score'] - b['hybrid_score'], 4),
            'before_rating': bp['rating_estimate'], 'after_rating': ap['rating_estimate'],
            'before_maps': bp['maps'], 'after_maps': ap['maps'],
            'before_mvp': bp['mvp'], 'after_mvp': ap['mvp'],
            'before_evp': bp['evp'], 'after_evp': ap['evp'],
            'honor_delta': round(r['layer1_honor_score'] - b['layer1_honor_score'], 3),
            'performance_correction_delta': round(r['layer2_residual_rf'] - b['layer2_residual_rf'], 3)})
    return {'mode': 'future_events', 'year': year, 'as_of': today.isoformat(),
        'schedule_verified_at': catalog['verified_at'], 'assumption_manifest': manifest,
        'rows': rows, 'excluded_records': excluded,
        'baseline_last_event_end': max(r['period_end'] for p in base for r in p['events']),
        'baseline_snapshot_updated': season.get('blum_2026_table', {}).get('updated_at'),
        'method': '固定已收录且已结束的赛事，追加假设参赛记录；Rating 按图数加权，综合分沿用年度双层评价。未设置的选手不追加成绩。MVP 为用户指定，不自动等同冠军。结果是条件推演，不是获奖概率或官方排名。'}
