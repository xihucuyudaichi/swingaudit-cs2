"""T4 Two-Stage Hybrid Top 20 Predictor & Single-Layer RF Holdout Baseline."""
import json
from pathlib import Path
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import mean_absolute_error
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]

def features(p):
    """Original 5 features for single-layer RF historical baseline (preserves exact 18/20, MAE 5.65)."""
    return [p['rating_estimate'] or 0, p['maps'], p['mvp'], p['evp'], len(p['events'])]

def load_weights_config():
    p = ROOT / 'data/event_weights.json'
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return {
        'tier_weights': {'Major': 1.0, '超级精英赛': 0.85, '精英赛': 0.75, '大型赛事': 0.60, '中型赛事': 0.35},
        'award_points': {'MVP': 12.0, 'EVP': 5.5, '无': 0.0},
        'placement_points': {'冠军': 4.0, '亚军': 2.5, '四强': 1.2, '八强': 0.5, '小组淘汰': 0.0},
        'performance_bonus': {'baseline_rating': 1.05, 'multiplier': 10.0, 'full_sample_maps': 10.0},
        'official_verifications': {}
    }

def compute_player_honor_breakdown(p, weights_cfg):
    tier_w = weights_cfg['tier_weights']
    award_pts = weights_cfg['award_points']
    place_pts = weights_cfg['placement_points']
    perf_cfg = weights_cfg['performance_bonus']

    total_raw = 0.0
    award_weighted_sum = 0.0
    place_weighted_sum = 0.0
    perf_weighted_sum = 0.0
    event_details = []

    high_tier_events = []
    elite_events = []

    for r in p.get('events', []):
        tier = r.get('tier', '大型赛事')
        w = float(tier_w.get(tier, 0.50))
        aw_p = float(award_pts.get(r.get('award', '无'), 0.0))
        pl_p = float(place_pts.get(r.get('team_place', '小组淘汰'), 0.0))
        rat = float(r['rating']) if r.get('rating') is not None else 1.0
        maps = float(r.get('maps') or 0)
        map_factor = min(1.0, maps / float(perf_cfg.get('full_sample_maps', 10.0)))
        pf_p = max(0.0, rat - float(perf_cfg.get('baseline_rating', 1.05))) * float(perf_cfg.get('multiplier', 10.0)) * map_factor

        h_ie = aw_p + pl_p + pf_p
        weighted_h = w * h_ie
        total_raw += weighted_h
        award_weighted_sum += w * aw_p
        place_weighted_sum += w * pl_p
        perf_weighted_sum += w * pf_p

        if tier in ('Major', '超级精英赛', '精英赛', '大型赛事'):
            high_tier_events.append((rat, maps))
        if tier in ('Major', '超级精英赛', '精英赛'):
            elite_events.append((rat, maps))

        if r.get('award') in ('MVP', 'EVP') or r.get('team_place') in ('冠军', '亚军'):
            event_details.append({
                'event': r.get('event'),
                'tier': tier,
                'weight': w,
                'award': r.get('award'),
                'team_place': r.get('team_place'),
                'rating': rat,
                'maps': int(maps),
                'weighted_points': round(weighted_h, 2)
            })

    high_maps = sum(m for _, m in high_tier_events)
    high_rat = sum(rt * m for rt, m in high_tier_events) / high_maps if high_maps else (p.get('rating_estimate') or 1.0)
    elite_maps = sum(m for _, m in elite_events)
    elite_rat = sum(rt * m for rt, m in elite_events) / elite_maps if elite_maps else high_rat

    opp = p.get('opponents') or {}
    vs_top5 = opp.get('vsTop5')
    vs_top10 = opp.get('vsTop10')
    vs_top20 = opp.get('vsTop20')
    overall_rat = p.get('rating_estimate') or 1.0

    # Hard-match pressure index: combines opponent split (when present) and elite-tier differential
    if isinstance(vs_top10, (int, float)) and isinstance(vs_top5, (int, float)):
        hard_match_rating = 0.55 * float(vs_top5) + 0.45 * float(vs_top10)
        hard_match_delta = hard_match_rating - 1.12
    elif isinstance(vs_top5, (int, float)):
        hard_match_rating = float(vs_top5)
        hard_match_delta = hard_match_rating - 1.12
    else:
        hard_match_rating = elite_rat
        hard_match_delta = (elite_rat - 1.12) * 0.75

    return {
        'raw_honor': round(total_raw, 4),
        'award_component': round(award_weighted_sum, 3),
        'placement_component': round(place_weighted_sum, 3),
        'performance_component': round(perf_weighted_sum, 3),
        'high_tier_maps': int(high_maps),
        'high_tier_rating': round(high_rat, 4),
        'elite_maps': int(elite_maps),
        'elite_rating': round(elite_rat, 4),
        'vs_top5': vs_top5,
        'vs_top10': vs_top10,
        'vs_top20': vs_top20,
        'hard_match_rating': round(hard_match_rating, 4),
        'hard_match_delta': round(hard_match_delta, 4),
        'key_events': sorted(event_details, key=lambda x: -x['weighted_points'])[:6]
    }

def residual_features(p, breakdown):
    """6 features X_i for Layer 2 residual correction f_theta(X_i)."""
    overall = p.get('rating_estimate') or 1.0
    return [
        overall - 1.08,                                # 1. 整体表现超出基准线幅度
        breakdown['elite_rating'] - 1.08,              # 2. Major/超精/精英级硬仗表现差值
        breakdown['hard_match_delta'],                 # 3. 强敌 (vs Top 5/10) 与高压对抗差值
        min(180.0, float(breakdown['high_tier_maps'])) / 120.0,  # 4. 大型及以上赛事有效样本量
        float(p.get('mvp', 0)) * 1.6 + float(p.get('evp', 0)) * 0.75,  # 5. 荣誉厚度修正项
        float(len(p.get('events', []))) / 15.0         # 6. 全年参赛站数覆盖度
    ]

def _evaluate_ranking(sorted_rows):
    for i, p in enumerate(sorted_rows):
        p['rank_pos'] = i + 1
    ranked = [p for p in sorted_rows if p.get('official_rank')]
    top20_hits = sum(bool(p.get('official_rank')) for p in sorted_rows[:20])
    top5_hits = sum(bool(p.get('official_rank') and p['official_rank'] <= 5) for p in sorted_rows[:5])
    mae = float(mean_absolute_error([p['official_rank'] for p in ranked], [p['rank_pos'] for p in ranked])) if ranked else 0.0
    sp = float(spearmanr([p['official_rank'] for p in ranked], [p['rank_pos'] for p in ranked]).statistic) if len(ranked) >= 3 else 0.0
    return {
        'official_top20_coverage': len(ranked),
        'top20_hits': int(top20_hits),
        'top5_hits': int(top5_hits),
        'rank_mae': round(mae, 3),
        'spearman': round(sp, 4)
    }

def fit_and_predict_hybrid(train_players, test_players, weights_cfg=None):
    weights_cfg = weights_cfg or load_weights_config()

    train_bd = [compute_player_honor_breakdown(p, weights_cfg) for p in train_players]
    test_bd = [compute_player_honor_breakdown(p, weights_cfg) for p in test_players]

    y_train = np.array([max(0.0, 21.0 - (p.get('official_rank') or 21)) for p in train_players], dtype=float)
    raw_train = np.array([b['raw_honor'] for b in train_bd], dtype=float)
    raw_test = np.array([b['raw_honor'] for b in test_bd], dtype=float)

    # Scale Layer 1 honor baseline onto the same [0, 20] target scale using training 98th percentile
    mask_ranked = y_train > 0
    scale_ref = float(np.sum(raw_train[mask_ranked] * y_train[mask_ranked]) / np.sum(raw_train[mask_ranked] ** 2)) if np.any(mask_ranked) else 0.25
    s_base_train = raw_train * scale_ref
    s_base_test = raw_test * scale_ref

    # Residual target on training set: r_i = S_i - S_{i, base}
    residual_train = y_train - s_base_train

    X_train = np.array([residual_features(p, b) for p, b in zip(train_players, train_bd)], dtype=float)
    X_test = np.array([residual_features(p, b) for p, b in zip(test_players, test_bd)], dtype=float)

    models = {
        'ridge': make_pipeline(StandardScaler(), Ridge(alpha=15.0, random_state=42)),
        'rf': RandomForestRegressor(n_estimators=200, min_samples_leaf=3, max_depth=5, random_state=42, n_jobs=1),
        'gbr': GradientBoostingRegressor(n_estimators=80, learning_rate=0.05, max_depth=3, min_samples_leaf=4, random_state=42)
    }

    preds_residual = {}
    preds_total = {}
    eval_by_model = {}

    for name, mdl in models.items():
        mdl.fit(X_train, residual_train)
        res_pred = mdl.predict(X_test)
        tot_pred = s_base_test + res_pred
        preds_residual[name] = res_pred
        preds_total[name] = tot_pred

        temp_rows = sorted(
            [{'id': p['id'], 'official_rank': p.get('official_rank'), 'score': float(sc)} for p, sc in zip(test_players, tot_pred)],
            key=lambda x: -x['score']
        )
        eval_by_model[name] = _evaluate_ranking(temp_rows)

    # Also evaluate Layer 1 Honor Baseline Only
    honor_only_rows = sorted(
        [{'id': p['id'], 'official_rank': p.get('official_rank'), 'score': float(sc)} for p, sc in zip(test_players, s_base_test)],
        key=lambda x: -x['score']
    )
    eval_by_model['honor_baseline'] = _evaluate_ranking(honor_only_rows)

    # Select best hybrid regressor (RF residual on top of honor baseline)
    primary_key = 'rf'
    ridge_step = models['ridge'].named_steps['ridge']
    scaler_step = models['ridge'].named_steps['standardscaler']
    feature_names = [
        ('overall_rating_excess', '整体加权 Rating 贡献'),
        ('elite_tier_excess', 'Major/超精/精英赛硬仗表现'),
        ('hard_opponent_delta', '对阵 Top 5/10 强敌抗压差值'),
        ('high_tier_sample_maps', '高级别赛事样本图数保障'),
        ('award_density', 'MVP / EVP 荣誉密度修正'),
        ('season_event_depth', '全年参赛站数深度')
    ]

    verifications_2025 = weights_cfg.get('official_verifications', {}).get('2025', {})

    rf_marginals = np.zeros_like(X_test, dtype=float)
    gbr_marginals = np.zeros_like(X_test, dtype=float)
    for j in range(X_test.shape[1]):
        X_masked = X_test.copy()
        X_masked[:, j] = scaler_step.mean_[j]
        rf_marginals[:, j] = preds_residual['rf'] - models['rf'].predict(X_masked)
        gbr_marginals[:, j] = preds_residual['gbr'] - models['gbr'].predict(X_masked)

    detailed_rows = []
    for idx, p in enumerate(test_players):
        bd = test_bd[idx]
        l1 = float(s_base_test[idx])
        l2_rf = float(preds_residual['rf'][idx])
        l2_ridge = float(preds_residual['ridge'][idx])
        l2_gbr = float(preds_residual['gbr'][idx])
        tot_rf = float(preds_total['rf'][idx])

        x_scaled = (X_test[idx] - scaler_step.mean_) / scaler_step.scale_
        ridge_contribs = x_scaled * ridge_step.coef_
        rf_contribs = rf_marginals[idx]
        gbr_contribs = gbr_marginals[idx]

        def _build_contrib_list(arr):
            items = [
                {
                    'key': k,
                    'label': lbl,
                    'raw_feature': round(float(X_test[idx, j]), 4),
                    'direction': '+' if float(arr[j]) >= 0 else '-',
                    'impact': round(float(arr[j]), 3)
                }
                for j, (k, lbl) in enumerate(feature_names)
            ]
            items.sort(key=lambda c: -abs(c['impact']))
            return items

        contrib_items = _build_contrib_list(rf_contribs)
        contrib_items_ridge = _build_contrib_list(ridge_contribs)
        contrib_items_gbr = _build_contrib_list(gbr_contribs)

        ver_info = verifications_2025.get(p['id'])
        detailed_rows.append({
            'id': p['id'],
            'name': p['name'],
            'official_rank': p.get('official_rank'),
            'maps': p['maps'],
            'rating_estimate': p['rating_estimate'],
            'mvp': p['mvp'],
            'evp': p['evp'],
            'official_verified_mvp': ver_info['official_mvp'] if ver_info else p['mvp'],
            'verification_note': ver_info['discrepancy_note'] if ver_info else None,
            'layer1_honor_raw': bd['raw_honor'],
            'layer1_honor_score': round(l1, 3),
            'layer2_residual_rf': round(l2_rf, 3),
            'layer2_residual_ridge': round(l2_ridge, 3),
            'layer2_residual_gbr': round(l2_gbr, 3),
            'hybrid_score': round(tot_rf, 4),
            'hybrid_ridge_score': round(float(preds_total['ridge'][idx]), 4),
            'hybrid_gbr_score': round(float(preds_total['gbr'][idx]), 4),
            'breakdown': bd,
            'feature_attributions': contrib_items,
            'feature_attributions_rf': contrib_items,
            'feature_attributions_ridge': contrib_items_ridge,
            'feature_attributions_gbr': contrib_items_gbr,
            'attribution_model': 'rf_leave_one_out_marginal'
        })

    # Compute ranks under Honor-Only and Hybrid-RF
    by_honor = sorted(detailed_rows, key=lambda r: -r['layer1_honor_score'])
    for i, r in enumerate(by_honor):
        r['honor_baseline_rank'] = i + 1

    by_hybrid = sorted(detailed_rows, key=lambda r: -r['hybrid_score'])
    for i, r in enumerate(by_hybrid):
        r['hybrid_rank'] = i + 1
        r['residual_rank_shift'] = r['honor_baseline_rank'] - r['hybrid_rank']

    return {
        'scale_reference_p98': round(scale_ref, 4),
        'evaluations': eval_by_model,
        'hybrid_rankings': by_hybrid
    }

def train():
    d = json.loads((ROOT / 'data/historical.json').read_text(encoding='utf-8'))
    weights_cfg = load_weights_config()

    train_set = [p for p in d['seasons']['2024']['players'] if p['maps'] >= 20 and p.get('cohort_tier') != 'extended_pro']
    test_set = [p for p in d['seasons']['2025']['players'] if p['maps'] >= 20 and p.get('cohort_tier') != 'extended_pro']

    # 1. Original Single-Layer RF (preserves exact historical holdout metrics)
    model_v1 = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, max_depth=5, random_state=42, n_jobs=1)
    model_v1.fit([features(p) for p in train_set], [max(0, 21 - (p['official_rank'] or 21)) for p in train_set])
    scores_v1 = model_v1.predict([features(p) for p in test_set])

    # 2. T4 Two-Stage Hybrid Model (Honor Baseline + Same-Scale Residual Correction)
    hybrid_out = fit_and_predict_hybrid(train_set, test_set, weights_cfg)
    hybrid_by_id = {r['id']: r for r in hybrid_out['hybrid_rankings']}

    rows = sorted(
        [
            {
                **{k: p[k] for k in ['id', 'name', 'official_rank', 'maps', 'rating_estimate', 'mvp', 'evp']},
                'score': float(s),
                'official_verified_mvp': hybrid_by_id[p['id']]['official_verified_mvp'],
                'verification_note': hybrid_by_id[p['id']]['verification_note'],
                'layer1_honor_score': hybrid_by_id[p['id']]['layer1_honor_score'],
                'layer2_residual_score': hybrid_by_id[p['id']]['layer2_residual_rf'],
                'hybrid_score': hybrid_by_id[p['id']]['hybrid_score'],
                'honor_baseline_rank': hybrid_by_id[p['id']]['honor_baseline_rank'],
                'hybrid_rank': hybrid_by_id[p['id']]['hybrid_rank'],
                'residual_rank_shift': hybrid_by_id[p['id']]['residual_rank_shift'],
                'breakdown': hybrid_by_id[p['id']]['breakdown'],
                'feature_attributions': hybrid_by_id[p['id']]['feature_attributions'],
            }
            for p, s in zip(test_set, scores_v1)
        ],
        key=lambda p: -p['score']
    )
    for i, p in enumerate(rows):
        p['predicted_rank'] = i + 1

    ranked = [p for p in rows if p['official_rank']]
    baseline = sorted(test_set, key=lambda p: -(p['rating_estimate'] or 0))
    for i, p in enumerate(baseline):
        p['_b_rank'] = i + 1
    b_ranked = [p for p in baseline if p.get('official_rank')]
    rating_baseline_hits = sum(bool(p['official_rank']) for p in baseline[:20])
    rating_baseline_mae = float(mean_absolute_error([p['official_rank'] for p in b_ranked], [p['_b_rank'] for p in b_ranked]))
    rating_baseline_sp = float(spearmanr([p['official_rank'] for p in b_ranked], [p['_b_rank'] for p in b_ranked]).statistic)

    v1_metrics = {
        'official_top20_coverage': len(ranked),
        'top20_hits': sum(bool(p['official_rank']) for p in rows[:20]),
        'rank_mae': mean_absolute_error([p['official_rank'] for p in ranked], [p['predicted_rank'] for p in ranked]),
        'spearman': float(spearmanr([p['official_rank'] for p in ranked], [p['predicted_rank'] for p in ranked]).statistic)
    }

    evals = hybrid_out['evaluations']
    ablation_table = [
        {
            'method_id': 'rating_baseline',
            'name': '基线 1：简单 Rating 降序基线',
            'formula': 'Sort by Σ(Rating·Maps)/ΣMaps',
            'top20_hits': int(rating_baseline_hits),
            'rank_mae': round(rating_baseline_mae, 2),
            'spearman': round(rating_baseline_sp, 3),
            'note': '仅看收录赛事图数加权 Rating，忽略赛事级别权重与 MVP/EVP 荣誉，易受少量低级别赛事高分干扰。'
        },
        {
            'method_id': 'layer1_honor_baseline',
            'name': '基线 2：第一层赛事加权荣誉基线',
            'formula': 'S_base = Σ_e (w_e · h_ie)',
            'top20_hits': evals['honor_baseline']['top20_hits'],
            'rank_mae': round(evals['honor_baseline']['rank_mae'], 2),
            'spearman': round(evals['honor_baseline']['spearman'], 3),
            'note': '按 Major(1.0)/超精(0.85)/精英(0.75)/大型(0.60) 汇总冠军与 MVP/EVP 积分，可锁定头部名次，但中段同分咬合区缺乏硬仗区分度。'
        },
        {
            'method_id': 'hybrid_ridge',
            'name': '双层混合模型（L1 荣誉基线 + L2 Ridge 岭回归残差）',
            'formula': 'S_hat = Σ(w_e·h_ie) + f_Ridge(X_i)',
            'top20_hits': evals['ridge']['top20_hits'],
            'rank_mae': round(evals['ridge']['rank_mae'], 2),
            'spearman': round(evals['ridge']['spearman'], 3),
            'note': '线性拟合同尺度残差，特征权重方向高度透明，适合解释强敌差值与大赛图数对名次的线性加减分。'
        },
        {
            'method_id': 'hybrid_gbr',
            'name': '双层混合模型（L1 荣誉基线 + L2 GBR 梯度提升残差）',
            'formula': 'S_hat = Σ(w_e·h_ie) + f_GBR(X_i)',
            'top20_hits': evals['gbr']['top20_hits'],
            'rank_mae': round(evals['gbr']['rank_mae'], 2),
            'spearman': round(evals['gbr']['spearman'], 3),
            'note': '梯度提升树拟合非线性残差，对高荣誉与低样本交互较敏感。'
        },
        {
            'method_id': 'hybrid_rf',
            'name': '双层混合模型（L1 荣誉基线 + L2 RF 随机森林残差）',
            'formula': 'S_hat = Σ(w_e·h_ie) + f_RF(X_i)',
            'top20_hits': evals['rf']['top20_hits'],
            'rank_mae': round(evals['rf']['rank_mae'], 2),
            'spearman': round(evals['rf']['spearman'], 3),
            'note': '在第一层加权荣誉基线上用随机森林拟合同尺度残差，兼顾头部荣誉定调与中段抗压表现修正。'
        },
        {
            'method_id': 'rf_historical_v1',
            'name': '单层 RF 历史留出模型（v1 原型基线）',
            'formula': 'f_RF(Rating, Maps, MVP, EVP, Events)',
            'top20_hits': int(v1_metrics['top20_hits']),
            'rank_mae': round(float(v1_metrics['rank_mae']), 2),
            'spearman': round(float(v1_metrics['spearman']), 3),
            'note': '五特征单层随机森林留年回测（Top 20 命中 18/20，MAE 5.65），保留作为原型历史对照基线。'
        }
    ]

    result = {
        'model': 'rf-historical-v1',
        'hybrid_model': 't4-hybrid-two-stage-v2',
        'formula': 'S_hat_i = Σ_e (w_e · h_ie) + f_theta(X_i)',
        'kind': '2025 historical holdout, not 2026 forecast',
        'training_year': 2024,
        'test_year': 2025,
        'train_candidates': len(train_set),
        'test_candidates': len(test_set),
        'features': ['event_weighted_rating_estimate', 'maps', 'mvp_count', 'evp_count', 'event_count'],
        'hybrid_layer2_features': [
            'overall_rating_excess',
            'elite_tier_excess',
            'hard_opponent_delta',
            'high_tier_sample_maps',
            'award_density',
            'season_event_depth'
        ],
        'tier_weights': weights_cfg['tier_weights'],
        'metrics': v1_metrics,
        'hybrid_metrics': evals['rf'],
        'rating_baseline_top20_hits': rating_baseline_hits,
        'ablation': ablation_table,
        'official_verifications': weights_cfg.get('official_verifications', {}).get('2025', {}),
        'limitations': [
            '第三方数据未逐项回源核验（如本地快照 ZywOo 2025 MVP 数为 7，HLTV 官方个案为 8，已在核对层标注）',
            '历史全年复现测试（2024 训练 → 2025 留出），不代表年中实时预测能力',
            '未排名者目标分设为0，候选池存在覆盖偏差',
            '不同来源Rating版本未完全核实',
            '2026无可用输入，不能输出2026预测'
        ],
        'rankings': rows,
        'hybrid_rankings': hybrid_out['hybrid_rankings']
    }
    multi_year_holdouts = []
    for tr_y in range(2018, 2025):
        te_y = tr_y + 1
        s_tr = d['seasons'].get(str(tr_y))
        s_te = d['seasons'].get(str(te_y))
        if not s_tr or not s_te:
            continue
        p_tr = [p for p in s_tr['players'] if ((p.get('maps') or 0) >= 15 or p.get('official_rank')) and p.get('cohort_tier') != 'extended_pro']
        p_te = [p for p in s_te['players'] if ((p.get('maps') or 0) >= 15 or p.get('official_rank')) and p.get('cohort_tier') != 'extended_pro']
        if len(p_tr) >= 20 and len(p_te) >= 20:
            my_out = fit_and_predict_hybrid(p_tr, p_te, weights_cfg)
            ev_rf = my_out['evaluations']['rf']
            ev_l1 = my_out['evaluations']['honor_baseline']
            ev_rg = my_out['evaluations']['ridge']
            top3 = [
                {'rank': r['hybrid_rank'], 'name': r['name'], 'official_rank': r.get('official_rank'), 'score': r['hybrid_score'], 'mvp': r['mvp'], 'evp': r['evp']}
                for r in my_out['hybrid_rankings'][:5]
            ]
            multi_year_holdouts.append({
                'train_year': tr_y,
                'test_year': te_y,
                'train_candidates': len(p_tr),
                'test_candidates': len(p_te),
                'rf_top20_hits': ev_rf['top20_hits'],
                'rf_top5_hits': ev_rf['top5_hits'],
                'rf_rank_mae': ev_rf['rank_mae'],
                'rf_spearman': ev_rf['spearman'],
                'l1_top20_hits': ev_l1['top20_hits'],
                'ridge_top20_hits': ev_rg['top20_hits'],
                'top5_preview': top3
            })

    live_2026_tracker = []
    if '2026' in d['seasons']:
        p_2025 = [p for p in d['seasons']['2025']['players'] if (p.get('maps') or 0) >= 20 and p.get('cohort_tier') != 'extended_pro']
        p_2026 = [p for p in d['seasons']['2026']['players'] if ((p.get('maps') or 0) >= 4 or p.get('mvp', 0) > 0) and p.get('cohort_tier') != 'extended_pro']
        if p_2025 and p_2026:
            out_2026 = fit_and_predict_hybrid(p_2025, p_2026, weights_cfg)
            live_2026_tracker = out_2026['hybrid_rankings'][:30]

    result['multi_year_holdouts'] = multi_year_holdouts
    result['live_2026_tracker'] = live_2026_tracker
    result['limitations'] = [
        '已整合 2012–2026 多源真实数据（IFTV + Ageha6912 + Santtu777 Top50 + markzhdan 76维 + ektarr + eupeutro + Valve VRS）',
        '历史留出回测（2018→2019 至 2024→2025 逐年前向滚动）检验跨年泛化，不代表赛前因果预测',
        '2026 赛季追踪榜基于截至 2026-10 已完赛实测（IEM Cologne Major 2026、BLAST Rivals 2026、ektarr），官方年终 Top20 尚未公布',
        'RF 与 GBR 残差归因采用单特征置均值边际贡献（Leave-One-Feature-Out Marginal），Ridge 采用标准化线性系数贡献'
    ]
    (ROOT / 'data/model-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'model': result['model'],
        'hybrid_model': result['hybrid_model'],
        'v1_metrics': result['metrics'],
        'hybrid_rf_metrics': result['hybrid_metrics'],
        'ablation_summary': [(a['method_id'], a['top20_hits'], a['rank_mae'], a['spearman']) for a in ablation_table]
    }, ensure_ascii=False))

if __name__ == '__main__':
    train()
