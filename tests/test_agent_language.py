import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import server

class AgentLanguageTests(unittest.TestCase):
    def test_internal_jargon_detected_without_rewriting_data_or_links(self):
        self.assertTrue(server.answer_language_issues('T2 聚类 k=4，cluster0，PCA与残差修正，同位置分位，awpy、TAPD。'))
        self.assertFalse(server.answer_language_issues('donk Rating 1.41，NiKo 1.13；两人打法相近。来源：https://example.com/T2/cluster0'))
    def test_jargon_answer_gets_plain_rewrite(self):
        call={'id':'c1','type':'function','function':{'name':'T1_multi_tier_query','arguments':'{"year":"2026","query":"donk","kind":"players"}'}}
        turns=[{'tool_calls':[call]},{'content':'T2聚类显示，两人属于cluster0。'},{'content':'两人打法相近，都主要承担突破职责。在当前收录赛事中，donk的表现更好。'}]
        with patch('server.request_chat',side_effect=turns) as chat,patch('server.execute_controlled_tool',return_value={'results':[{'name':'donk','maps':30}]}):
            r=server.agent('donk与NiKo谁强','2026')
            self.assertFalse(server.answer_language_issues(r['answer']))
            self.assertEqual(r['runtime']['answer_repairs'],1)
            self.assertIn('普通CS2观众',chat.call_args_list[0].args[0][0]['content'])

if __name__=='__main__':unittest.main()
