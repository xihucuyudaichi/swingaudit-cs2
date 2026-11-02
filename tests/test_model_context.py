import copy
import io
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import model_context as context
import lab_provider
import server

class ModelContextTests(unittest.TestCase):
    def test_large_report_is_valid_bounded_and_keeps_full_trace(self):
        result = server.execute_controlled_tool('T4_hybrid_predict', {'year':'2026','player':'all'})
        original = copy.deepcopy(result)
        history = [{'role':'user','content':'donk强还是载物强'}, {'role':'tool','tool_call_id':'a','content':json.dumps(result,ensure_ascii=False)}]
        prepared = context.prepare_history(history)
        self.assertLessEqual(context.size(prepared),context.MAX_HISTORY_BYTES)
        summary=json.loads(prepared[1]['content'])
        self.assertTrue(summary['_context_summary']['partial'])
        self.assertIn('data',summary)
        self.assertEqual(result,original)
        self.assertEqual(json.loads(history[1]['content']),original)

    def test_repeated_results_and_escaped_unicode_stay_within_budget(self):
        data={'results':[{'name':'选手'+str(i),'rating':1.41,'source':{'source_file':'official.xlsx','row':i+1},'history':['\\\"中文'*100]*30} for i in range(30)]}
        history=[{'role':'user','content':'测试'}]+[{'role':'tool','tool_call_id':str(i),'content':json.dumps(data,ensure_ascii=False)} for i in range(24)]
        result=context.prepare_history(history)
        self.assertLessEqual(context.size(result),context.MAX_HISTORY_BYTES)
        self.assertEqual([m['tool_call_id'] for m in result[1:]],[str(i) for i in range(24)])
        for message in result[1:]:json.loads(message['content'])

    def test_small_evidence_numbers_and_provenance_are_unchanged(self):
        data={'results':[{'name':'donk','rating':1.41,'source_file':'input.xlsx','row':17,'source_url':'https://example.com'}]}
        self.assertEqual(json.loads(context.summarize_tool(data)),data)

    def test_seven_calls_execute_six_and_answer_all_call_ids(self):
        calls=[{'id':str(i),'type':'function','function':{'name':'T1_multi_tier_query','arguments':json.dumps({'year':'2026','query':'player'+str(i),'kind':'players'})}} for i in range(7)]
        with patch('server.execute_controlled_tool',return_value={'results':[{'name':'donk','maps':30}]}) as execute, patch('server.request_chat',side_effect=[{'tool_calls':calls},{'content':'已有记录支持进行有限比较。'}]) as chat:
            response=server.agent('donk强还是载物强','2026')
            self.assertEqual(execute.call_count,6)
            self.assertEqual(len(response['tools']),6)
            history=chat.call_args.args[0]
            replies=[m for m in history if m['role']=='tool']
            self.assertEqual(len(replies),7)
            self.assertTrue(json.loads(replies[-1]['content'])['not_executed'])

    def test_http_errors_are_classified_without_leaking_details(self):
        cases=[(400,'maximum context length input_tokens secret-key','超出模型'),(400,'bad schema secret-key','未能接受'),(401,'secret-key','认证失败'),(429,'secret-key','繁忙'),(503,'secret-key','暂时不可用')]
        for status,detail,hint in cases:
            with self.subTest(status=status), patch('lab_provider.read_config',return_value={'base_url':'http://localhost/v1','api_key':'secret-key'}), patch('lab_provider.urllib.request.build_opener') as factory:
                factory.return_value.open.side_effect=urllib.error.HTTPError('http://localhost',status,'error',{},io.BytesIO(detail.encode()))
                with self.assertLogs(level='WARNING') as logs, self.assertRaises(lab_provider.ProviderError) as error:
                    lab_provider.request_chat([])
                self.assertIn(hint,str(error.exception));self.assertNotIn('secret-key',str(error.exception));self.assertNotIn('secret-key',' '.join(logs.output))

if __name__=='__main__':unittest.main()
