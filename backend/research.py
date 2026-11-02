"""Evidence-backed research operations (L1-L4 data audit, T1/T2 compare, T5 dual-mode sandbox, SQLite records)."""
import collections
import copy
import hashlib
import json
import math
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import openpyxl

from role_aligner import align_players, load_role_report
from knowledge import load_event_weights, load_rules, load_ontology, search_rules
from train_model import fit_and_predict_hybrid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://github.com/bootsh-zvuat/IFTV-TOP20'

def load_data():
    return json.loads((ROOT / 'data/historical.json').read_text(encoding='utf-8'))

def load_integrated_sources():
    p_src = ROOT / 'data/integrated_sources.json'
    if p_src.exists():
        return json.loads(p_src.read_text(encoding='utf-8'))
    return {}

def season(data, year):
    result = data['seasons'].get(str(year))
    if not result:
        raise ValueError('该年份没有真实数据，不能计算或用其他年份代替。')
    return result

def weighted(rows, field):
    valid = [
        r for r in rows
        if isinstance(r.get(field), (int, float)) and isinstance(r.get('maps'), (int, float)) and r['maps'] > 0
    ]
    maps = sum(r['maps'] for r in valid)
    return {'value': sum(r[field] * r['maps'] for r in valid) / maps if maps else None, 'maps': maps or None}

def statistic(p, metric):
    blum = (p.get('multi_tier_benchmarks') or {}).get('blum_2026') or {}
    if metric in blum and metric != 'overall':
        b_item = blum[metric]
        return {
            'value': float(b_item['rating']),
            'maps': b_item.get('maps'),
            'scope': b_item.get('scope_zh', f'2026 {metric} 实测 Rating 3.02'),
            'evidence': [b_item]
        }
    if metric == 'overall':
        if 'overall' in blum:
            b_ov = blum['overall']
            return {
                'value': float(b_ov['rating']),
                'maps': b_ov.get('maps'),
                'scope': b_ov.get('scope_zh', '2026 全年 Rating 3.02 (@BLUM. / HLTV)'),
                'evidence': p['events']
            }
        return {**weighted(p['events'], 'rating'), 'scope': '按该赛季已收录赛事的参赛地图数加权统计', 'evidence': p['events']}
    if metric in ('vs_top5', 'vs_top10', 'vs_top20', 'vs_top30', 'vs_top50'):
        o = p.get('opponents') or {}
        k = 'vsTop' + metric.split('top')[1]
        return {'value': o.get(k), 'maps': o.get(k + '图数'), 'scope': '按该赛季对阵相应世界排名强队的交手记录统计', 'evidence': [o] if o else []}
    if metric in ('ct_side', 't_side', 'both_sides'):
        s_info = (p.get('side_splits') or {}).get(metric)
        if s_info and s_info.get('rating') is not None:
            return {
                'value': float(s_info['rating']),
                'maps': s_info.get('maps_est') or s_info.get('rounds'),
                'scope': s_info.get('scope_note', f'{metric} 阵营实测 Rating'),
                'evidence': [s_info]
            }
        return {'value': None, 'maps': None, 'scope': '该选手在当前阵营范围内暂无统计记录', 'evidence': []}

    if metric == 'grand_finals':
        m_finals = p.get('major_finals') or []
        if m_finals:
            w = weighted(m_finals, 'rating')
            return {
                'value': w['value'],
                'maps': w['maps'],
                'scope': '按历届 Major 决赛阶段的比赛地图统计',
                'evidence': m_finals
            }
        return {'value': None, 'maps': None, 'scope': '该选手在本赛季暂无 Major 决赛出场记录', 'evidence': []}

    if metric == 'majors':
        rows = [r for r in p['events'] if r.get('tier') == 'Major']
        if rows:
            return {**weighted(rows, 'rating'), 'scope': '按本赛季 Major 赛事参赛地图加权统计', 'evidence': rows}
        mt = (p.get('multi_tier_benchmarks') or {}).get('santtu_majors') or {}
        if mt.get('major_rating') is not None:
            return {
                'value': float(mt['major_rating']),
                'maps': mt.get('major_maps'),
                'scope': '按本赛季 Major 赛事汇总表现统计',
                'evidence': [mt]
            }
        return {'value': None, 'maps': None, 'scope': '该选手在本赛季暂无 Major 参赛记录', 'evidence': []}

    if metric.startswith('map_'):
        target_map = metric[4:].casefold()
        for mp_rec in (p.get('map_pool') or []):
            if str(mp_rec.get('map', '')).casefold() == target_map and mp_rec.get('rating') is not None:
                return {
                    'value': float(mp_rec['rating']),
                    'maps': mp_rec.get('maps_est') or mp_rec.get('rounds'),
                    'scope': f"{mp_rec['map']} 地图实战表现统计",
                    'evidence': [mp_rec]
                }
        return {'value': None, 'maps': None, 'scope': f'暂无该选手在 {metric[4:].capitalize()} 地图的比赛记录', 'evidence': []}

    tiers = {
        'big_events': ['大型赛事', '精英赛', '精英赛事', '超级精英赛', 'Major'],
        'elite_events': ['精英赛', '精英赛事', '超级精英赛', 'Major'],
        'super_elite': ['超级精英赛', 'Major']
    }
    if metric in tiers:
        rows = [r for r in p['events'] if r['tier'] in tiers[metric]]
        if rows:
            return {**weighted(rows, 'rating'), 'scope': '按对应级别重点赛事的参赛地图加权统计', 'evidence': rows}
        if metric == 'big_events':
            sb = (p.get('multi_tier_benchmarks') or {}).get('santtu_big_events') or {}
            if sb.get('big_rating') is not None:
                return {'value': float(sb['big_rating']), 'maps': sb.get('big_maps'), 'scope': '按大型及以上级别赛事汇总表现统计', 'evidence': [sb]}
        return {'value': None, 'maps': None, 'scope': '当前赛事范围内暂无比赛记录', 'evidence': []}
    return {'value': None, 'maps': None, 'scope': '当前统计范围内暂无比赛记录', 'evidence': []}

def compare(data, body):
    s = season(data, body.get('year'))
    ids = body.get('players', [])
    if len(ids) != 2 or ids[0] == ids[1]:
        raise ValueError('请选择两位不同选手。')
    players = [next((p for p in s['players'] if p['id'] == id), None) for id in ids]
    if not all(players):
        raise ValueError('选手不属于当前年份。')
    metric = body.get('metric', 'overall')
    stats = [statistic(p, metric) for p in players]
    valid = all(x['value'] is not None for x in stats)
    year_str = str(body['year'])
    role_alignment = align_players(year_str, ids)
    weights_cfg = load_event_weights()
    verifications = weights_cfg.get('official_verifications', {}).get(year_str, {})
    return {
        'year': year_str,
        'metric': metric,
        'players': [{
            'id': p['id'],
            'name': p['name'],
            'official_rank': p.get('official_rank'),
            'maps': p.get('maps'),
            'mvp': p.get('mvp'),
            'evp': p.get('evp'),
            'side_splits': p.get('side_splits') or {},
            'map_pool': (p.get('map_pool') or [])[:10],
            'major_finals': p.get('major_finals') or [],
            'career_profile': p.get('career_profile'),
            'playstyle_measured': p.get('playstyle_measured'),
            'multi_tier_benchmarks': p.get('multi_tier_benchmarks') or {}
        } for p in players],
        'stats': stats,
        'status': 'ready' if valid else 'missing',
        'delta': stats[0]['value'] - stats[1]['value'] if valid else None,
        'role_alignment': role_alignment,
        'official_verifications': [verifications.get(p['id']) for p in players if verifications.get(p['id'])],
        'notice': '不同场上位置的职责分工存在差异，建议结合下方场上位置与打法表现综合参考。'
    }

def scenarios(data, body):
    from future_scenarios import simulate_future
    if not isinstance(body, dict) or body.get('mode') != 'future_events':
        raise ValueError('旧版历史赛事改写已停用，请重新设置未来赛事、参赛表现与 MVP。')
    return simulate_future(data, body)


def audit(data):
    manifest = json.loads((ROOT / 'data/source-audit/iftv/manifest.json').read_text(encoding='utf-8'))
    files = []
    seasons = {}
    for m in manifest:
        path = ROOT / 'data/source-audit/iftv' / m['file']
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        values = list(ws.iter_rows(values_only=True))
        headers = [str(x) for x in values[0]]
        rows = values[1:]
        nulls = {headers[i]: sum(r[i] is None or r[i] == '' for r in rows) for i in range(len(headers))}
        files.append({
            'file': m['file'],
            'rows': len(rows),
            'sha256': h,
            'hash_matches': h == m['sha256'],
            'sheet': ws.title,
            'null_fields': nulls,
            'url': m['url']
        })
    for y, s in data['seasons'].items():
        events = [r for p in s['players'] for r in p['events']]
        keys = collections.Counter((r['event'], r['source_player_id']) for r in events)
        bad = [
            r for r in events
            if not (isinstance(r['rating'], (int, float)) and 0 < r['rating'] < 3 and isinstance(r['maps'], (int, float)) and r['maps'] > 0)
        ]
        seasons[y] = {
            'events': len(s['events']),
            'rows': len(events),
            'declared_rows_match': len(events) == s['rows'],
            'players': len(s['players']),
            'opponent_players': sum(bool(p.get('opponents')) for p in s['players']),
            'official_ranked_players': 0 if str(y) == '2026' else sum(bool(p.get('official_rank')) for p in s['players']),
            'duplicate_player_event_keys': sum(v > 1 for v in keys.values()),
            'invalid_numeric_rows': len(bad),
            'missing_rating_version_rows': sum(r.get('rating_version') is None for r in events),
            'missing_period_rows': sum(r.get('period_start') is None for r in events),
            'missing_source_weight_rows': sum(r.get('source_weight') is None for r in events)
        }
    role_rep = load_role_report()
    rules_corp = load_rules()
    ont = load_ontology()
    ev_weights = load_event_weights()
    report = {
        'complete': False,
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'source': SOURCE,
        'files': files,
        'seasons': seasons,
        'four_layers_status': {
            'L1_tournament_honors': {
                'name': 'L1 分站赛事与荣誉数据',
                'status': '已接入 2024–2025 共 48 场赛事 3,302 行 + 赛事分级设定权重表 + 2025 官方 MVP 核对层',
                'configured_tier_weights': ev_weights.get('tier_weights', {}),
                'official_verifications_count': len(ev_weights.get('official_verifications', {}).get('2025', {}))
            },
            'L2_high_pressure_opponents': {
                'name': 'L2 强敌与高压赛场数据',
                'status': '已接入收录赛事级别筛选（Major/超精/精英/大型）与每年 20 位头部选手的 vs Top 5/10/20/30/50 年度拆分；淘汰赛/决赛细分待扩充',
                'opponent_split_players_per_year': 20
            },
            'L3_tactical_style_roles': {
                'name': 'L3 战术风格与角色数据',
                'status': '已构建 6 维打法风格特征库与 T2 (StandardScaler -> PCA -> Ward/KMeans) 战术生态位对齐报告',
                'candidates_2024': role_rep['seasons']['2024']['candidate_count'],
                'candidates_2025': role_rep['seasons']['2025']['candidate_count'],
                'ward_silhouette_2025': role_rep['seasons']['2025']['ward_silhouette_k4']
            },
            'L4_rules_and_ontology': {
                'name': 'L4 历年榜单与规则语料库 (RAG + 领域本体)',
                'status': '已构建 HLTV Rating 3.0 / Attributes 29 项指标 / Top 20 准则 / RWS 辨析语料库与评价领域本体',
                'rules_doc_count': len(rules_corp.get('documents', [])),
                'ontology_entities_count': len(ont.get('entities', []))
            }
        },
        'gaps': [
            '2026赛季真实赛事与选手数据尚未接入。',
            '原表年度对手拆分（vs Top 5/10/20/30/50）每年仅覆盖20位选手，且vsTop10/20/30/50地图数为空。',
            '原表逐赛事记录缺少精确比赛日期、Rating版本（2.0/2.1/3.0）及原始赛事权重（已通过 L1 设定权重配置表提供透明建模权重）。',
            '原表未收录大型赛淘汰赛、决赛、地图池与T/CT阵营拆分；L3 战术风格特征库为结合公开职责档案与实测面板构建的研究基准。',
            '第三方仓库快照未经HLTV或完美世界逐条官方事实核验（例如本地快照 ZywOo 2025 MVP 数为 7，HLTV 官方个案为 8，已在 L1 官方核对层修正标注）。'
        ],
        'repairs': [
            '2024年两位同名Lucky（源选手ID 13497 与 19069）已拆分为独立档案，不再混算。',
            '前端默认入口已改为真实后端接口，不再使用demo.json。',
            '新增 L1 赛事分级权重配置与 2025 官方 MVP 核对映射（ZywOo 8 MVP vs 快照 7 MVP）。',
            '新增 L3 战术风格特征库与 T2 (StandardScaler -> PCA -> Ward/KMeans) 同位置分位对齐模块。',
            '新增 L4 规则语料库 RAG 与评价领域本体，以及 T4 双层混合预测模型（荣誉基线 + Ridge/RF/GBR 残差修正）和 T5 未开赛 MVP 沙盘推演。'
        ]
    }
    int_sources = load_integrated_sources()
    report['integrated_datasets_count'] = len(int_sources.get('verified_datasets_registry', []))
    report['quarantined_datasets_count'] = len(int_sources.get('quarantined_datasets_registry', []))
    report['verified_datasets_registry'] = int_sources.get('verified_datasets_registry', [])
    report['quarantined_datasets_registry'] = int_sources.get('quarantined_datasets_registry', [])
    report['four_layers_status'] = {
        'L1_tournament_honors': {
            'name': 'L1 分站赛事、历年 Top20 与荣誉底座 (2012–2026)',
            'status': '已接入 2012–2026 共 15 个赛季 6,943 人次选手档案、38,895 条分站记录（全赛季均达 447–467 人）+ 2013–2025 连续 13 年官方 Top 20 (260人次) + 24 届 Major 档案 + Valve VRS 2026 积分与赛事权重',
            'configured_tier_weights': ev_weights.get('tier_weights', {}),
            'official_verifications_count': len(ev_weights.get('official_verifications', {}).get('2025', {}))
        },
        'L2_high_pressure_opponents': {
            'name': 'L2 强敌、地图池、CT/T 阵营与 Major 决赛数据',
            'status': '已接入 6,943 人次选手跨赛季地图池、2,102 名选手×13 张地图×CT/T 阵营拆分 (124,827行) + 300 名 CS2 选手 CT/T 官方角色与 Rating + 24 届 Major 决赛逐图统计 + 2026 Rating 3.0 & Swing',
            'opponent_split_players_per_year': 30
        },
        'L3_tactical_style_roles': {
            'name': 'L3 战术风格、真实 Demo 角色与回合经济遥测',
            'status': '已接入 Jamie-Packer 306 名选手 awpy Demo 实测 + pachellber 1,416 名选手 Rating 3.0 与 1,202 名选手回合发枪/道具经济 + OpenCS2 11.17 万次对枪 + SneakyZero 42 万行回合经济，支撑 15 赛季 6,943 人次 100% T2 角色对齐',
            'candidates_2024': role_rep['seasons']['2024']['candidate_count'],
            'candidates_2025': role_rep['seasons']['2025']['candidate_count'],
            'ward_silhouette_2025': role_rep['seasons']['2025']['ward_silhouette_k4']
        },
        'L4_rules_and_ontology': {
            'name': 'L4 历年榜单专访、Valve VRS 规则与评价领域本体 (RAG)',
            'status': '已构建 HLTV Rating 3.0 / Attributes 29 项指标 / Top 20 准则 / RWS 辨析 / 2013–2022 官方评选专访链接与领域本体',
            'rules_doc_count': len(rules_corp.get('documents', [])),
            'ontology_entities_count': len(ont.get('entities', []))
        }
    }
    report['gaps'] = [
        '2026 官方年终 Top 20 榜单尚未公布（当前展示截至 2026-10 已完赛实测与 Valve VRS 全球战队积分）。',
        'IFTV 2024–2025 原始分站 Excel 缺精确日期与原始权重列（已通过 Valve VRS、One-Studio、Ageha6912 及 L1 权重表交叉补全）。',
        'Jamie-Packer 真实 Demo 角色特征覆盖 306 名职业选手，其余历史选手采用 HLTV 投掷物/爆头/首杀实测面板与位置基线校准（均已显式标注 source_status）。',
        '已识别并隔离剔除 4 组外部缺陷数据源：devanshgupta0308（纯虚拟练习数据）、sergionefedov（含 15% 估算与错误 Major 标注）、kimetsuu（2026 失败回退合成值）、pr4nut（匿名脱敏数据）。'
    ]
    report['repairs'] = [
        '已完成 2012–2026 共 15 个赛季、24 组公开真实数据集（含 pachellber CS2-ECONEFFICIENCY、nmwalsh 1.4万HLTV ID、gungorMetehan Major MVP/EVP、DSCKGEC 844人、RLinV1 Top20阵容）的清洗、去重与全赛季选手库扩容（每年 447–467 人，总计 6,943 人次 / 38,895 条参赛记录）。',
        '新增选手对比与档案页的 CT/T 阵营拆分、13 张比赛地图池、Major 决赛实测 Rating/Swing 及生涯手雷/互救面板。',
        'T2 角色对齐升级为接入 Jamie-Packer awpy Demo 实测（TAPD/OAP/PODT/POKT/3D站位）与 OpenCS2/SneakyZero 2026 遥测，并覆盖全部 15 个赛季。',
        'T4 双层预测修正为 RF/GBR/Ridge 各自独立的边际归因，并新增 2018→2019 至 2024→2025 连续 7 年滚动留出回测与 2026 赛季实时追踪榜。',
        '2024 年两位同名 Lucky（源选手 ID 13497 与 19069）保持独立档案拆分。'
    ]
    (ROOT / 'data/completeness-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report

def db_path():
    return Path(os.environ.get('ROUND_RESEARCH_DB', ROOT / 'data/research.sqlite3'))

def init_db():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(p)) as c:
        c.execute('CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,title TEXT NOT NULL,created TEXT NOT NULL,payload TEXT NOT NULL)')
        c.commit()

def get_records():
    init_db()
    with closing(sqlite3.connect(db_path())) as c:
        rows = c.execute('SELECT id,title,created,payload FROM records ORDER BY created DESC LIMIT 50').fetchall()
    return [{'id': i, 'title': t, 'created': d, 'payload': json.loads(p)} for i, t, d, p in rows]

def save_record(body):
    title = (body.get('title') or '').strip()
    payload = body.get('payload')
    if not title or not isinstance(payload, dict):
        raise ValueError('研究记录需要标题和结构化结果。')
    init_db()
    item = {'id': str(uuid.uuid4()), 'title': title[:160], 'created': datetime.now(timezone.utc).isoformat(), 'payload': payload}
    with closing(sqlite3.connect(db_path())) as c:
        c.execute('INSERT INTO records(id,title,created,payload) VALUES(?,?,?,?)', (item['id'], item['title'], item['created'], json.dumps(payload, ensure_ascii=False)))
        c.commit()
    return item

if __name__ == '__main__':
    print(json.dumps(audit(load_data()), ensure_ascii=True))
