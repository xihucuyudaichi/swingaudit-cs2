import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import server
from site_discovery import search_site_data, question_scope

class SiteDiscoveryTests(unittest.TestCase):
    def test_global_question_does_not_inherit_page_pair(self):
        year,names=question_scope('你觉得26年世界第一自由人是谁','2025',{'selected_players':['donk','zywoo']},server.DATA)
        self.assertEqual(year,'2026');self.assertEqual(names,[])
        year,names=question_scope('这两个人谁更强？','2026',{'selected_players':['donk','zywoo']},server.DATA)
        self.assertEqual(set(names),{'donk','ZywOo'})
        self.assertEqual(question_scope('ropz和NiKo这两个人谁更强','2026',{'selected_players':['donk','zywoo']},server.DATA)[1],[])
    def test_all_role_candidates_paginated_with_key_players(self):
        all_rows=[];offset=0
        while True:
            r=search_site_data(server.DATA,server.ROLE_REPORT,{'year':'2026','kind':'players','role':'自由人','limit':4,'offset':offset})
            all_rows+=r['results']
            if r['next_offset'] is None:break
            offset=r['next_offset']
        self.assertGreater(len(all_rows),8);self.assertEqual(len(all_rows),r['total_matches']);self.assertEqual(r['scanned_count'],len(server.DATA['seasons']['2026']['players']))
        ids={p['id'] for p in all_rows};self.assertTrue({'ropz','kscerato','spinx'}<=ids);self.assertNotIn('donk',ids);self.assertNotIn('zywoo',ids)
        self.assertEqual(len(ids),len(all_rows))
        for row in all_rows:
            original=next(p for p in server.DATA['seasons']['2026']['players'] if p['id']==row['id'])
            self.assertEqual(row['rating_estimate'],original['rating_estimate']);self.assertEqual(row['maps'],original['maps']);self.assertTrue(row['source'])
    def test_name_team_search_and_events(self):
        r=search_site_data(server.DATA,server.ROLE_REPORT,{'year':'2026','kind':'players','query':'KSCERATO'})
        self.assertEqual(r['results'][0]['id'],'kscerato')
        r=search_site_data(server.DATA,server.ROLE_REPORT,{'year':'2026','kind':'events','query':'科隆'})
        self.assertTrue(r['results']);self.assertTrue(r['results'][0]['source_url'])
    def test_missing_year_and_role_are_explicit(self):
        self.assertTrue(search_site_data(server.DATA,server.ROLE_REPORT,{'year':'2027','kind':'players'})['missing'])
        self.assertTrue(search_site_data(server.DATA,server.ROLE_REPORT,{'year':'2026','kind':'players','role':'不存在的位置'})['missing'])
    def test_empty_roles_does_not_default_to_pair(self):
        result=server.query({'year':'2026','kind':'roles','query':''})
        self.assertGreater(result['total_matches'],2)
    def test_open_role_question_seeds_site_discovery(self):
        with patch('server.request_chat',return_value={'content':'当前库的自由人候选包括ropz和KSCERATO，需要结合不同赛事表现判断。'}) as chat:
            result=server.agent('你觉得26年世界第一自由人是谁','2026',{'selected_players':['donk','zywoo']})
            self.assertEqual(result['tools'][0]['invoked_name'],'search_site_data')
            self.assertGreater(result['tools'][0]['result']['total_matches'],8)
            user=next(m['content'] for m in chat.call_args.args[0] if m['role']=='user')
            self.assertNotIn('donk',user);self.assertNotIn('zywoo',user.lower())
    def test_explicit_player_keeps_detail_tool_flow(self):
        with patch('server.request_chat',return_value={'content':'no evidence'}) as chat:
            with self.assertRaisesRegex(RuntimeError,'no evidence'):server.agent('比较donk和ropz','2026',{'selected_players':['donk','zywoo']})
            self.assertFalse(any(m['role']=='tool' for m in chat.call_args.args[0]))
    def test_null_metrics_remain_missing(self):
        data={'seasons':{'2026':{'players':[{'id':'x','name':'X','maps':5,'rating_estimate':None,'opponents':None,'multi_tier_benchmarks':None}], 'events':[]}}}
        result=search_site_data(data,{'seasons':{}},{'year':'2026','kind':'players'})
        self.assertIsNone(result['results'][0]['vs_top5']);self.assertIsNone(result['results'][0]['rating_estimate'])
    def test_pagination_schema_rejects_invalid_arguments(self):
        from agent_tools import ToolSession
        from agent_policy import read_policy
        with patch('server.execute_controlled_tool') as execute:
            s=ToolSession(server.TOOLS,execute,read_policy(),float('inf'))
            for args in [{'year':'2026','kind':'players','limit':10000},{'year':'2026','kind':'players','offset':-1}]:
                self.assertEqual(s.call('search_site_data',args)[1]['error'],'invalid_arguments')
            execute.assert_not_called()

    def test_floating_page_and_selection_context_scope(self):
        year, names = question_scope('他今年的防守方表现如何？', '2026', {'focused_player': 'donk', 'page_name': '选手档案 · donk'}, server.DATA)
        self.assertEqual(year, '2026')
        self.assertEqual(names, ['donk'])
        year2, names2 = question_scope('为什么这项数据这么突出？', '2026', {'selected_text': 'm0NESY · 1.35 · 142图 · MVP', 'selected_kind': '页面点选'}, server.DATA)
        self.assertEqual(year2, '2026')
        self.assertIn('m0NESY', names2)
        with patch('server.request_chat', side_effect=[
            {'content': None, 'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {'name': 'T1_multi_tier_query', 'arguments': '{"year":"2026","query":"donk","kind":"players"}'}}]},
            {'content': 'donk 在 2026 赛季已收录赛事中的综合 Rating 为 1.41（来源：IFTV 历史快照）。'}
        ]) as chat:
            res = server.agent('他今年的比赛表现如何？', '2026', {
                'focused_player': 'donk',
                'page_name': '选手档案 · donk',
                'page_summary': '正在浏览选手 donk 的 2026 赛季档案',
                'selected_text': 'donk · Spirit · 147 图',
                'selected_kind': '页面点选'
            })
            self.assertIn('1.41', res['answer'])
            user_msg = next(m['content'] for m in chat.call_args_list[0].args[0] if m['role'] == 'user')
            self.assertIn('当前所在页面：选手档案 · donk', user_msg)
            self.assertIn('用户在页面中页面点选的内容：donk · Spirit · 147 图', user_msg)

if __name__=='__main__':unittest.main()
