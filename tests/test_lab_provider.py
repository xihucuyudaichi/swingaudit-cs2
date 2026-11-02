import io
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import lab_provider
import server

class LabProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'credentials.py'
        self.source.write_text("API_KEY = 'offline-lab-key'\nraise RuntimeError('Do not execute this file')\n",encoding='utf-8')
        self.config=self.root/'lab.json';self.config.write_text(json.dumps({'base_url':'http://127.0.0.1:12345/v1','credential_source':str(self.source)}),encoding='utf-8')
        self.env=patch.dict(os.environ,{'ROUND_LAB_CONFIG':str(self.config)});self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def test_credentials_parsed_without_execution_or_exposure(self):
        self.assertEqual(lab_provider.read_config()['api_key'],'offline-lab-key')
        status=lab_provider.provider_status();self.assertTrue(status['configured']);self.assertEqual(status['model'],'qwen3.8-27b')
        self.assertNotIn('offline-lab-key',json.dumps(status))
    def test_active_backend_uses_lab_model(self):
        self.assertEqual(server.MODEL,'qwen3.8-27b');self.assertEqual(server.request_chat.__module__,'lab_provider')
    def test_protocol_and_reasoning_filter(self):
        upstream={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'ok','reasoning_content':'private'}}]}
        with patch('lab_provider.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value=io.BytesIO(json.dumps(upstream).encode())
            result=lab_provider.request_chat([{'role':'user','content':'test'}],server.TOOLS,True)
            request=factory.return_value.open.call_args.args[0];payload=json.loads(request.data)
            self.assertEqual(payload['model'],'qwen3.8-27b');self.assertEqual(payload['tool_choice'],'required')
            self.assertFalse(payload['chat_template_kwargs']['enable_thinking']);self.assertNotIn('reasoning_content',result)
    def test_unavailable_credentials_actionable(self):
        self.source.write_text('API_KEY = None',encoding='utf-8')
        with self.assertRaises(lab_provider.ProviderNotConfigured):lab_provider.request_chat([])

class AgentLoadingRegressionTests(unittest.TestCase):
    def test_truncated_and_filtered_responses_are_rejected(self):
        for reason, hint in [('length', '内容过长'), ('content_filter', '换一种表述')]:
            upstream = {'choices': [{'finish_reason': reason, 'message': {'content': 'partial'}}]}
            with patch('lab_provider.read_config', return_value={'base_url': 'http://localhost/v1', 'api_key': 'test'}), patch('lab_provider.urllib.request.build_opener') as factory:
                factory.return_value.open.return_value = io.BytesIO(json.dumps(upstream).encode())
                with self.assertRaisesRegex(lab_provider.ProviderError, hint):
                    lab_provider.request_chat([])

    def test_remaining_deadline_caps_provider_timeout(self):
        upstream = {'choices': [{'finish_reason': 'stop', 'message': {'content': 'ok'}}]}
        with patch('lab_provider.read_config', return_value={'base_url': 'http://localhost/v1', 'api_key': 'test'}), patch('lab_provider.urllib.request.build_opener') as factory:
            factory.return_value.open.return_value = io.BytesIO(json.dumps(upstream).encode())
            lab_provider.request_chat([], timeout_seconds=3)
            self.assertAlmostEqual(factory.return_value.open.call_args.kwargs['timeout'], 3, delta=0.05)
            self.assertEqual(json.loads(factory.return_value.open.call_args.args[0].data)['max_tokens'], 8192)

    def test_agent_deadline_prevents_another_model_request(self):
        with patch('server.time.monotonic', side_effect=[0, 111]), patch('server.request_chat') as chat:
            with self.assertRaisesRegex(lab_provider.ProviderError, '超时'):
                server.agent('donk', '2026')
            chat.assert_not_called()

    def test_cancelled_browser_does_not_trigger_another_error_response(self):
        handler = object.__new__(server.Handler)
        with patch.object(handler, 'send_response', side_effect=ConnectionAbortedError):
            handler.send(200, {'answer': 'complete'})

    def test_last_turn_synthesizes_without_tools(self):
        call = {'id': 'c1', 'type': 'function', 'function': {'name': 'T1_multi_tier_query', 'arguments': '{"year":"2026","query":"donk","kind":"players"}'}}
        turns = [{'tool_calls': [{**call, 'id': 'c' + str(i)}]} for i in range(4)] + [{'content': '根据收录记录进行比较。'}]
        with patch('server.request_chat', side_effect=turns) as chat, patch('server.execute_controlled_tool', return_value={'results': [{'name': 'donk', 'maps': 30}]}):
            result = server.agent('donk', '2026')
            self.assertEqual(len(result['tools']), 1)
            self.assertEqual(result['runtime']['cache_hits'], 3)
            self.assertEqual(chat.call_args.args[1], server.TOOLS)
            self.assertTrue(chat.call_args.kwargs['force_text'])
            self.assertFalse(chat.call_args.kwargs['require_tool'])

if __name__=='__main__':unittest.main()
