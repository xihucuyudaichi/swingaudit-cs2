"""Sequential live test of the lab model with the application's actual Agent logic."""
import json
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import lab_provider
import server

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'verification/lab-speed-20261023.json'
report={'model':lab_provider.MODEL,'started_at':datetime.now(timezone.utc).isoformat(),'mode':'sequential, non-streaming; full response latency','agent_path':'actual backend Agent function in isolated process; active website unchanged during benchmark','thinking':False,'samples':[],'model_requests':[]}
def timed_chat(messages,tools=None,require_tool=False):
    start=time.perf_counter()
    try:
        message=lab_provider.request_chat(messages,tools,require_tool)
        report['model_requests'].append({'seconds':round(time.perf_counter()-start,3),'success':True,'tool_calls':len(message.get('tool_calls') or []),'response_chars':len(message.get('content') or '')})
        return message
    except Exception:
        report['model_requests'].append({'seconds':round(time.perf_counter()-start,3),'success':False});raise
server.request_chat=timed_chat
server.MODEL=lab_provider.MODEL
def save():TARGET.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def run(kind,label,action):
    start=time.perf_counter();request_count=len(report['model_requests'])
    try:details=action();sample={'kind':kind,'label':label,'success':True,**details}
    except Exception as e:
        sample={'kind':kind,'label':label,'success':False,'error_type':type(e).__name__}
        if isinstance(e,lab_provider.ProviderError):sample['error']=str(e)
    sample['seconds']=round(time.perf_counter()-start,3);sample['model_roundtrips']=len(report['model_requests'])-request_count
    report['samples'].append(sample);save();print(json.dumps(sample,ensure_ascii=True),flush=True)
def short():
    response=timed_chat([{'role':'user','content':'Reply exactly ROUND_OK, with no other text.'}]);text=response.get('content') or ''
    if text.strip()!='ROUND_OK':raise RuntimeError('Unexpected short answer')
    return {'response_chars':len(text),'reply_verified':True}
def agent(question):
    result=server.agent(question,'2025')
    if result.get('model')!=lab_provider.MODEL or not result.get('tools') or not result.get('answer'):raise RuntimeError('Missing evidence')
    return {'response_chars':len(result['answer']),'tool_calls':len(result['tools']),'tool_arguments':[t['arguments'] for t in result['tools']],'lookup_result_counts':[len(t['result'].get('results',[])) for t in result['tools']]}
for i in range(3):run('short_direct',f'short-{i+1}',short)
run('agent_backend','single-player',lambda:agent('查询donk在2025年收录赛事的总图数、赛事数和来源文件，100字内回答并说明不是全年完整统计。'))
run('agent_backend','two-player-comparison',lambda:agent('请比较donk和ZywOo在2025年收录赛事的Rating近似、地图数和MVP数，给出来源文件。200字内说明差异及数据覆盖限制。'))
report['summary']={}
for kind in ('short_direct','agent_backend'):
    rows=[s for s in report['samples'] if s['kind']==kind];ok=[s['seconds'] for s in rows if s['success']]
    report['summary'][kind]={'attempts':len(rows),'successes':len(ok),'mean_seconds':round(statistics.mean(ok),3) if ok else None,'median_seconds':round(statistics.median(ok),3) if ok else None,'min_seconds':min(ok) if ok else None,'max_seconds':max(ok) if ok else None}
report['finished_at']=datetime.now(timezone.utc).isoformat();save();print(json.dumps({'summary':report['summary']},ensure_ascii=True),flush=True)
