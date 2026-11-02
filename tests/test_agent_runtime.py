import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import agent_policy
import lab_provider
import server
from agent_tools import ToolSession


def call(i='c1', args=None, name='T1_multi_tier_query'):
    return {'id': i, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args or {'year':'2026','query':'donk','kind':'players'})}}


class ToolRuntimeTests(unittest.TestCase):
    def setUp(self):self.policy=agent_policy.read_policy()
    def test_invalid_arguments_never_execute_and_model_can_correct(self):
        bad=call();bad['function']['arguments']='{bad json'
        turns=[{'tool_calls':[bad]},{'tool_calls':[call('c2')]},{'content':'依据收录数据比较。'}]
        with patch('server.request_chat',side_effect=turns) as chat, patch('server.execute_controlled_tool',return_value={'results':[{'name':'donk','maps':30}]}) as execute:
            r=server.agent('donk','2026')
            self.assertEqual(execute.call_count,1);self.assertEqual(r['runtime']['tool_errors'],1)
            self.assertEqual(json.loads(chat.call_args_list[1].args[0][-1]['content'])['error'],'invalid_arguments')

    def test_schema_enum_type_missing_extra_and_nonfinite(self):
        from unittest.mock import Mock
        execute=Mock();session=ToolSession(server.TOOLS,execute,self.policy,float('inf'))
        for args in [{'year':'2099','query':'donk','kind':'players'}, {'year':2026,'query':'donk','kind':'players'}, {'query':'donk'}, {'year':'2026','query':'donk','kind':'players','extra':1}, [], {'year':'2026','query':float('nan'),'kind':'players'}]:
            _, result, fresh=session.call('T1_multi_tier_query',args)
            self.assertFalse(fresh);self.assertEqual(result['error'],'invalid_arguments')
        execute.assert_not_called()
        self.assertEqual(session.call({}, {})[1]['error'],'unknown_tool')

    def test_cache_is_per_run_and_preserves_evidence(self):
        from unittest.mock import Mock
        execute=Mock(return_value={'results':[{'maps':147,'source_file':'original.xlsx','row':3}]})
        s=ToolSession(server.TOOLS,execute,self.policy,float('inf'))
        args={'year':'2026','query':'donk','kind':'players'}
        first=s.call('T1_multi_tier_query',args)
        second=s.call('T1_multi_tier_query',json.dumps(dict(reversed(list(args.items())))))
        self.assertEqual(execute.call_count,1);self.assertTrue(first[2]);self.assertFalse(second[2]);self.assertEqual(first[1],second[1])
        ToolSession(server.TOOLS,execute,self.policy,float('inf')).call('T1_multi_tier_query',args)
        self.assertEqual(execute.call_count,2)

    def test_total_budget_switches_to_explicit_final_mode(self):
        policy={**self.policy,'max_tool_executions':2}
        calls=[call(str(i),{'year':'2026','query':str(i),'kind':'players'}) for i in range(3)]
        with patch('server.read_policy',return_value=policy), patch('server.request_chat',side_effect=[{'tool_calls':calls},{'content':'基于现有证据给出结论。'}]) as chat, patch('server.execute_controlled_tool',return_value={'results':[{'maps':30}]}) as execute:
            r=server.agent('测试','2026');self.assertEqual(execute.call_count,2)
            self.assertTrue(chat.call_args.kwargs['force_text']);self.assertEqual(r['runtime']['model_requests'],2)
            self.assertEqual(json.loads(chat.call_args.args[0][-2]['content'])['error'],'tool_budget')

    def test_invalid_answer_is_rewritten_not_relabelled(self):
        turns=[{'tool_calls':[call()]},{'content':'donk Rating 999'},{'content':'donk Rating 1.41，仅供当前数据范围参考。'}]
        with patch('server.request_chat',side_effect=turns), patch('server.execute_controlled_tool',return_value={'results':[{'maps':30}]}):
            r=server.agent('donk','2026');self.assertNotIn('999',r['answer']);self.assertEqual(r['runtime']['answer_repairs'],1)
            self.assertEqual(r['verification']['status'],'remediated_after_rollback')
        with patch('server.request_chat',side_effect=turns[:2]+[{'content':'donk Rating 999'}]), patch('server.execute_controlled_tool',return_value={'results':[{'maps':30}]}):
            with self.assertRaisesRegex(lab_provider.ProviderError,'未通过证据核对'):server.agent('donk','2026')

    def test_deadline_prevents_tool_execution(self):
        from unittest.mock import Mock
        execute=Mock();s=ToolSession(server.TOOLS,execute,self.policy,0)
        with self.assertRaises(lab_provider.ProviderError):s.call('T1_multi_tier_query',{'year':'2026','query':'donk','kind':'players'})
        execute.assert_not_called()

    def test_invalid_policy_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'policy.json'
            for change in [{'max_model_turns':True},{'run_timeout_seconds':999},{'http_max_retries':-1},{'unexpected':'secret-key'}]:
                path.write_text(json.dumps({**self.policy,**change}),encoding='utf-8')
                with patch.dict(os.environ,{'ROUND_AGENT_POLICY':str(path)}),self.assertRaises(lab_provider.ProviderNotConfigured):agent_policy.read_policy()


class ProviderRetryTests(unittest.TestCase):
    def setUp(self):
        self.policy=agent_policy.read_policy()
        self.config=patch('lab_provider.read_config',return_value={'base_url':'http://localhost/v1','api_key':'private-key'});self.config.start();self.addCleanup(self.config.stop)
    def response(self):return io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':'ok'}}]}).encode())
    def error(self,status,header=None):return urllib.error.HTTPError('http://localhost',status,'error',header or {},io.BytesIO(b'private-key'))
    def test_transient_retry_respects_remaining_time_and_final_tool_choice(self):
        clock=[0.0];requests=[]
        def open_request(req,timeout):
            requests.append((json.loads(req.data),timeout))
            if len(requests)==1:
                clock[0]+=10;raise self.error(429,{'Retry-After':'1'})
            return self.response()
        with patch('lab_provider.urllib.request.build_opener') as factory, patch('lab_provider.time.monotonic',side_effect=lambda:clock[0]), patch('lab_provider.time.sleep',side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)):
            factory.return_value.open.side_effect=open_request
            r=lab_provider.request_chat([],server.TOOLS,force_text=True,timeout_seconds=30,policy=self.policy)
            self.assertEqual([x[1] for x in requests],[30,19]);self.assertEqual(r['_telemetry']['http_attempts'],2)
            self.assertEqual(requests[1][0]['tool_choice'],'none');self.assertIn('tools',requests[1][0])
            self.assertFalse(requests[1][0]['chat_template_kwargs']['enable_thinking'])
    def test_terminal_errors_do_not_retry(self):
        for code in [400,401,403,404]:
            with patch('lab_provider.urllib.request.build_opener') as factory,patch('lab_provider.time.sleep') as sleep:
                factory.return_value.open.side_effect=self.error(code)
                with self.assertRaises(lab_provider.ProviderError) as error:lab_provider.request_chat([],policy=self.policy)
                self.assertEqual(factory.return_value.open.call_count,1);sleep.assert_not_called();self.assertNotIn('private-key',str(error.exception))
    def test_retry_budget_and_long_retry_after(self):
        for errors in [[self.error(503),self.error(503)],[self.error(429,{'Retry-After':'120'})]]:
            with patch('lab_provider.urllib.request.build_opener') as factory,patch('lab_provider.time.sleep') as sleep:
                factory.return_value.open.side_effect=errors
                with self.assertRaises(lab_provider.ProviderError):lab_provider.request_chat([],policy=self.policy)
                self.assertEqual(factory.return_value.open.call_count,len(errors))
                self.assertEqual(sleep.call_count,len(errors)-1)
    def test_retry_cannot_extend_deadline(self):
        clock=[0.0]
        def fail(*args,**kwargs):clock[0]=29.5;raise self.error(503)
        with patch('lab_provider.urllib.request.build_opener') as factory,patch('lab_provider.time.monotonic',side_effect=lambda:clock[0]),patch('lab_provider.time.sleep') as sleep:
            factory.return_value.open.side_effect=fail
            with self.assertRaises(lab_provider.ProviderError):lab_provider.request_chat([],timeout_seconds=30,policy=self.policy)
            self.assertEqual(factory.return_value.open.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
