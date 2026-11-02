"""Agnes protocol tests against a local fake HTTP service; no real API calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import provider
import server

class AgnesProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.config=Path(self.tmp.name)/'config.json'
        self.env=patch.dict(os.environ,{'ROUND_AGNES_CONFIG':str(self.config)});self.env.start()
        self.agent_client=patch('server.request_chat',provider.request_chat);self.agent_client.start()
        self.agent_model=patch('server.MODEL',provider.MODEL);self.agent_model.start()
        self.config.write_text(json.dumps({'api_key':''}),encoding='utf-8')
        self.requests=[];self.responses=[]
    def tearDown(self):
        self.agent_model.stop();self.agent_client.stop();self.env.stop();self.tmp.cleanup()
    def serve(self):
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                owner.requests.append({'path':self.path,'auth':self.headers.get('Authorization'),'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
                status,body=owner.responses.pop(0)
                raw=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
        http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
        self.addCleanup(http.server_close);self.addCleanup(http.shutdown)
        self.config.write_text(json.dumps({'api_key':'offline-test-key','base_url':f'http://127.0.0.1:{http.server_port}/v1'}),encoding='utf-8')
    def test_blank_key_stops_before_network(self):
        with patch('provider.urllib.request.build_opener',side_effect=AssertionError('Network must not be called')):
            with self.assertRaises(provider.ProviderNotConfigured) as error:provider.request_chat([{'role':'user','content':'test'}])
        self.assertIn('api_key',str(error.exception));self.assertIn(str(self.config),str(error.exception))
        self.assertEqual(provider.provider_status()['provider_status'],'missing_api_key')
        self.assertNotIn('api_key',provider.provider_status())
    def test_real_tool_roundtrip_protocol_offline(self):
        self.serve()
        self.responses=[(200,{'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'reasoning_content':'hidden','tool_calls':[{'id':'call_1','type':'function','function':{'name':'query_research','arguments':json.dumps({'year':'2025','kind':'players','query':'donk'})}}]}}]}),
                        (200,{'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'根据源记录，donk在收录赛事中共128图；并非全年完整统计。'}}]})]
        result=server.agent('查询donk图数','2025')
        self.assertEqual(result['model'],'agnes-3.0-flash');self.assertEqual(len(result['tools']),1)
        self.assertEqual(result['tools'][0]['result']['results'][0]['maps'],128)
        first,second=self.requests
        self.assertEqual(first['path'],'/v1/chat/completions');self.assertEqual(first['auth'],'Bearer offline-test-key')
        self.assertEqual(first['body']['tool_choice'],'required');self.assertEqual(second['body']['tool_choice'],'auto')
        self.assertEqual(first['body']['model'],'agnes-3.0-flash');self.assertFalse(first['body']['chat_template_kwargs']['enable_thinking'])
        self.assertFalse(first['body']['stream']);self.assertEqual(first['body']['max_tokens'],2048)
        self.assertEqual(first['body']['tools'][0]['function']['name'],'query_research')
        tool=second['body']['messages'][-1];self.assertEqual(tool['role'],'tool');self.assertEqual(tool['tool_call_id'],'call_1')
        self.assertNotIn('reasoning_content',second['body']['messages'][-2]);self.assertNotIn('offline-test-key',json.dumps(result))
    def test_upstream_errors_do_not_echo_secret_or_body(self):
        self.serve();self.responses=[(401,{'error':'sensitive upstream debug offline-test-key'})]
        with self.assertRaises(provider.ProviderError) as error:provider.request_chat([])
        self.assertIn('401',str(error.exception));self.assertNotIn('offline-test-key',str(error.exception));self.assertNotIn('sensitive',str(error.exception))
    def test_incomplete_output_is_not_accepted(self):
        self.serve();self.responses=[(200,{'choices':[{'finish_reason':'length','message':{'role':'assistant','content':'partial'}}]})]
        with self.assertRaises(provider.ProviderError):provider.request_chat([])
    def test_answer_without_evidence_is_rejected(self):
        self.serve();self.responses=[(200,{'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'unverified claim'}}]})]
        with self.assertRaisesRegex(RuntimeError,'no evidence'):server.agent('test','2025')
    def test_config_hot_reload(self):
        self.assertFalse(provider.provider_status()['configured'])
        self.config.write_text(json.dumps({'api_key':'offline-test-key'}),encoding='utf-8')
        self.assertEqual(provider.provider_status()['provider_status'],'configured_unverified')

if __name__=='__main__':unittest.main()
