import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import research

class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=research.load_data()
    def test_source_integrity_and_counts(self):
        r=research.audit(self.data)
        self.assertFalse(r['complete']);self.assertTrue(all(f['hash_matches'] for f in r['files']))
        self.assertEqual(r['seasons']['2024']['rows']+r['seasons']['2025']['rows'],3694);self.assertEqual(len(r['seasons']),15);self.assertEqual(sum(s['rows'] for s in r['seasons'].values()),38895);self.assertTrue(all(s['players']>=440 for s in r['seasons'].values()))
        self.assertTrue(all(s['declared_rows_match'] and s['duplicate_player_event_keys']==0 and s['invalid_numeric_rows']==0 for s in r['seasons'].values()))
    def test_lucky_identity_split(self):
        rows=[p for p in self.data['seasons']['2024']['players'] if p['name']=='Lucky']
        self.assertEqual(len(rows),2);self.assertEqual(len({p['id'] for p in rows}),2)
        self.assertTrue(all(len(p['source_ids'])==1 for p in rows))
    def test_comparison_independent_recalculation(self):
        result=research.compare(self.data,{'year':'2025','metric':'overall','players':['donk','zywoo']})
        for stat,id in zip(result['stats'],['donk','zywoo']):
            p=next(p for p in self.data['seasons']['2025']['players'] if p['id']==id)
            expected=sum(r['rating']*r['maps'] for r in p['events'])/sum(r['maps'] for r in p['events'])
            self.assertAlmostEqual(stat['value'],expected)
            self.assertTrue(all(r['source_file'] and r['row']>=2 for r in stat['evidence']))
    def test_missing_scope_and_year(self):
        r=research.compare(self.data,{'year':'2025','metric':'grand_finals','players':['donk','zywoo']})
        self.assertEqual(r['status'],'missing');self.assertIsNone(r['delta'])
        c2026=research.compare(self.data,{'year':'2026','players':['donk','zywoo']});self.assertEqual(c2026['status'],'ready');
        with self.assertRaises(ValueError):research.compare(self.data,{'year':'2027','players':['donk','zywoo']})
        with self.assertRaises(ValueError):research.compare(self.data,{'year':'2025','players':['donk','donk']})
    def test_annual_opponent_scope(self):
        p=next(p for p in self.data['seasons']['2025']['players'] if p['id']=='donk')
        r=research.statistic(p,'vs_top5');self.assertEqual(r['value'],1.37);self.assertEqual(r['maps'],58)
        self.assertEqual(r['evidence'][0]['sheet'],'opponent')
        self.assertIsNone(research.statistic(p,'vs_top10')['maps'])
    def test_old_historical_scenario_contract_rejected(self):
        with self.assertRaises(ValueError):
            research.scenarios(self.data, {'year': '2025', 'event': 'IEM Chengdu 2025', 'player': 'donk', 'rating': 2})

    def test_server_records_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=os.environ.get('ROUND_RESEARCH_DB');os.environ['ROUND_RESEARCH_DB']=str(Path(tmp)/'research.sqlite3')
            try:
                item=research.save_record({'title':'测试记录','payload':{'type':'compare','year':'2025'}})
                self.assertEqual(research.get_records(),[item])
            finally:
                if old is None:os.environ.pop('ROUND_RESEARCH_DB',None)
                else:os.environ['ROUND_RESEARCH_DB']=old
    def test_active_frontend_has_no_demo_import(self):
        src=research.ROOT/'src';text=''.join((src/f).read_text(encoding='utf-8-sig') for f in ['main.jsx','ConnectedApp.jsx'])
        self.assertNotIn("from './demo.json'",text);self.assertNotIn('setTimeout(()=>{const c=compare',text)
    def test_agent_lookup_extracts_real_player_names(self):
        import server
        r=server.query({'year':'2025','kind':'players','query':'donk 2025 收录赛事 总图数 赛事数'})
        self.assertEqual(r['total_matches'],1);self.assertEqual(r['results'][0]['id'],'donk')
        r=server.query({'year':'2025','kind':'players','query':'比较donk和ZywOo的Rating'})
        self.assertEqual({p['id'] for p in r['results']},{'donk','zywoo'})
    def test_agent_lookup_never_invents_missing_names(self):
        import server
        r=server.query({'year':'2025','kind':'players','query':'unknown-player-938272'})
        self.assertEqual(r['results'],[]);self.assertEqual(r['total_matches'],0);self.assertTrue(r['query_hint'])


    def test_step1_l1_weights_and_l4_rules_rag(self):
        import knowledge
        weights = knowledge.load_event_weights()
        self.assertEqual(weights['tier_weights']['Major'], 1.0)
        self.assertEqual(weights['official_verifications']['2025']['zywoo']['official_mvp'], 8)
        self.assertEqual(weights['official_verifications']['2025']['zywoo']['snapshot_mvp'], 7)
        rag = knowledge.search_rules('RWS 天梯 与 Rating 3.0 保枪出口击杀', top_k=3)
        rule_ids = {r['rule_id'] for r in rag['results']}
        self.assertTrue({'RULE-RWS-01', 'RULE-R30-02'} & rule_ids)

    def test_step2_t4_two_stage_hybrid_model_and_ablation(self):
        report = json.loads((research.ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
        self.assertEqual(report['hybrid_model'], 't4-hybrid-two-stage-v2')
        self.assertGreaterEqual(len(report['ablation']), 6)
        self.assertEqual(report['hybrid_metrics']['top5_hits'], 5)
        top_row = report['hybrid_rankings'][0]
        self.assertEqual(top_row['id'], 'zywoo')
        self.assertEqual(top_row['official_verified_mvp'], 8)
        self.assertTrue(len(top_row['feature_attributions']) >= 4)

    def test_step3_t2_role_cluster_aligner_and_t5_future_mvp_sandbox(self):
        import role_aligner
        aligned = role_aligner.align_players('2025', ['donk', 'ropz'])
        self.assertFalse(aligned['same_tactical_niche'])
        self.assertEqual(len(aligned['players']), 2)
        self.assertGreater(aligned['ward_silhouette_k4'], 0.7)
    def test_step4_planner_tools_verifier_closed_loop_and_rollback(self):
        import server
        from unittest.mock import patch
        plan = server.plan_task('如果年底 Major 是 donk 拿 MVP，排名会怎么变？', '2025')
        self.assertEqual(plan['task_type'], 'what_if_simulation')
        self.assertIn('T5_what_if_sandbox', plan['recommended_tools'])
        # Test T1-T5 controlled tool execution
        t2_out = server.execute_controlled_tool('T2_role_align', {'year': '2025', 'players': ['donk', 'zywoo']})
        self.assertEqual(len(t2_out['players']), 2)
        t3_out = server.execute_controlled_tool('T3_claim_fact_check', {'year': '2025', 'claim': '只会保枪 RWS', 'player': 'ropz'})
        self.assertTrue(len(t3_out['matched_rules']) >= 1)
        t5_out = server.execute_controlled_tool('T5_what_if_sandbox', {'year': '2025', 'event': 'Major December 2025', 'mvp_player': 'donk'})
        self.assertEqual(t5_out['mode'], 'future_events')
        self.assertTrue(t5_out['requires_input'])
        # Test Verifier automatic rollback remediation when first tool query returns 0 matches
        fake_turns = [
            {'content': None, 'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {'name': 'T1_multi_tier_query', 'arguments': json.dumps({'year': '2025', 'query': 'nonexistent_long_string_xyz', 'kind': 'players'})}}]},
            {'content': '首次未查到有效记录。', 'tool_calls': []},
            {'content': '已根据回退补查的 donk 记录完成核验。', 'tool_calls': []}
        ]
        with patch('server.request_chat', side_effect=fake_turns):
            res = server.agent('请核验 donk 的表现', '2025')
        self.assertEqual(res['verification']['status'], 'remediated_after_rollback')
        self.assertEqual(len(res['tools']), 2)
        self.assertTrue(all(t['tool'] == 'query_research' for t in res['tools']))


    def test_step5_multi_source_2012_2026_and_strict_verifier(self):
        import server
        import role_aligner
        # 1. All 15 seasons (2012-2026) present in historical.json and role-report.json
        self.assertEqual(sorted(list(self.data['seasons'].keys())), [str(y) for y in range(2012, 2027)])
        role_rep = role_aligner.load_role_report()
        self.assertEqual(sorted(list(role_rep['seasons'].keys())), [str(y) for y in range(2012, 2027)])
        # 2. CT/T side, Map Pool, and Major Grand Finals comparison scopes
        ct_cmp = research.compare(self.data, {'year': '2025', 'metric': 'ct_side', 'players': ['donk', 'zywoo']})
        self.assertEqual(ct_cmp['status'], 'ready')
        self.assertIsNotNone(ct_cmp['delta'])
        mp_cmp = research.compare(self.data, {'year': '2025', 'metric': 'map_mirage', 'players': ['donk', 'zywoo']})
        self.assertEqual(mp_cmp['status'], 'ready')
        gf_cmp = research.compare(self.data, {'year': '2025', 'metric': 'grand_finals', 'players': ['zywoo', 'ropz']})
        self.assertEqual(gf_cmp['status'], 'ready')
        gf_2026 = research.compare(self.data, {'year': '2026', 'metric': 'grand_finals', 'players': ['m0nesy', 'niko']})
        self.assertEqual(gf_2026['status'], 'ready')
        # 3. Jamie-Packer real demo playstyle metrics attached
        zywoo_2024 = next(p for p in self.data['seasons']['2024']['players'] if p['id'] == 'zywoo')
        self.assertIsNotNone(zywoo_2024.get('playstyle_measured'))
        self.assertGreater(zywoo_2024['playstyle_measured']['map_count'], 50)
        # 4. Multi-year holdouts & 2026 live tracker & RF marginal attributions in model-report.json
        report = json.loads((research.ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report.get('multi_year_holdouts', [])), 7)
        self.assertGreaterEqual(len(report.get('live_2026_tracker', [])), 20)
        top_row = report['hybrid_rankings'][0]
        self.assertEqual(top_row.get('attribution_model'), 'rf_leave_one_out_marginal')
        self.assertTrue(len(top_row.get('feature_attributions_ridge', [])) >= 4)
        # 5. Strict Verifier rejects empty evidence and hallucinated Rating numbers
        plan = server.plan_task('donk 2025', '2025')
        probe = server.verify_trace_and_answer('donk 2025', '2025', plan, [{'result': {'results': []}}], 'donk Rating 999')
        self.assertFalse(probe['passed'])
        self.assertEqual(probe['status'], 'failed_verification')


    def test_valve_vrs_completeness(self):
        sources = research.load_integrated_sources()
        vrs = sources.get('valve_vrs', {})
        self.assertEqual(vrs.get('snapshot_date'), '2026-11-01')
        top50 = vrs.get('global_top50_2026', [])
        self.assertEqual(len(top50), 50)
        self.assertEqual(top50[0]['team'], 'MOUZ')
        self.assertAlmostEqual(top50[0]['points'], 1959.0, places=1)
        self.assertEqual(top50[1]['team'], 'Vitality')
        self.assertAlmostEqual(top50[1]['points'], 1920.0, places=1)
        self.assertEqual(top50[2]['team'], 'FURIA')
        self.assertAlmostEqual(top50[2]['points'], 1910.5, places=1)
        for row in top50:
            self.assertNotIn(row.get('bounty_offered'), (None, '', '—'))
            self.assertNotIn(row.get('bounty_collected'), (None, '', '—'))
            self.assertNotIn(row.get('opponent_network'), (None, '', '—'))
            self.assertNotIn(row.get('lan_wins'), (None, '', '—'))
            self.assertIsNotNone(row.get('starting_rank_value'))
            self.assertIsNotNone(row.get('h2h_adjustments'))
        self.assertEqual(len(vrs.get('global_top50_2026_oct05', [])), 50)
        self.assertEqual(vrs['global_top50_2026_oct05'][0]['team'], 'Spirit')
        self.assertEqual(len(vrs.get('regions_2026', {}).get('europe', [])), 30)
        self.assertEqual(len(vrs.get('regions_2026', {}).get('americas', [])), 20)
        self.assertEqual(len(vrs.get('regions_2026', {}).get('asia', [])), 20)
        self.assertEqual(vrs['regions_2026']['asia'][0]['team'], 'The MongolZ')
        self.assertAlmostEqual(vrs['regions_2026']['asia'][0]['points'], 1553.0, places=1)
        self.assertEqual(len(vrs.get('by_year', {}).get('2025', [])), 30)
        self.assertEqual(len(vrs.get('by_year', {}).get('2024', [])), 30)
        self.assertEqual(len(vrs.get('major_invitations_2026', {}).get('singapore_major', {}).get('teams', [])), 32)
        self.assertEqual(len(vrs.get('major_invitations_2026', {}).get('cologne_major', {}).get('teams', [])), 32)

        report = json.loads((research.ROOT / 'data/model-report.json').read_text(encoding='utf-8'))
        tracker = report.get('live_2026_tracker', [])
        self.assertEqual(len(tracker), 30)
        for idx, r in enumerate(tracker, 1):
            self.assertEqual(r['hybrid_rank'], idx)
            self.assertAlmostEqual(r['layer1_honor_score'] + r['layer2_residual_rf'], r['hybrid_score'], places=2)

if __name__=='__main__':unittest.main()
