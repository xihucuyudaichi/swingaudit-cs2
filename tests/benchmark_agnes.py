"""Small sequential live benchmark. Saves timings only, never API credentials."""
import json
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime,timezone
import urllib.request
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import provider

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'verification/agnes-speed-20261023.json'
report={'model':provider.MODEL,'started_at':datetime.now(timezone.utc).isoformat(),
        'mode':'sequential, non-streaming; full response latency, not time-to-first-token',
        'thinking':False,'samples':[],'comparison_with_gemini':'not measured in this run'}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def save():TARGET.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def run(kind,label,action):
    start=time.perf_counter()
    try:
        details=action();sample={'kind':kind,'label':label,'success':True,**details}
    except Exception as e:
        sample={'kind':kind,'label':label,'success':False,'error_type':type(e).__name__}
        if isinstance(e,provider.ProviderError):sample['error']=str(e)
    sample['seconds']=round(time.perf_counter()-start,3);report['samples'].append(sample);save()
    print(json.dumps(sample,ensure_ascii=True),flush=True)
def short():
    r=provider.request_chat([{'role':'user','content':'Reply exactly ROUND_OK, with no other text.'}]);text=r.get('content') or ''
    if text.strip()!='ROUND_OK':raise RuntimeError('Unexpected short answer')
    return {'response_chars':len(text),'reply_verified':True}
def agent(question):
    req=urllib.request.Request('http://127.0.0.1:5177/api/agent',data=json.dumps({'year':'2025','question':question}).encode(),headers={'Content-Type':'application/json'})
    try:
        with opener.open(req,timeout=330) as res:r=json.load(res)
    except urllib.error.HTTPError as e:
        try:body=json.load(e)
        except ValueError:body={}
        safe={'http_status':e.code,'error_type':body.get('type','HTTPError')}
        if body.get('type') in ('ProviderError','ProviderNotConfigured'):safe['error']=body.get('error')
        e.close();raise provider.ProviderError(json.dumps(safe,ensure_ascii=True)) from None
    if r.get('model')!=provider.MODEL or not r.get('answer') or not r.get('tools'):raise RuntimeError('Unverified agent result')
    return {'response_chars':len(r['answer']),'tool_calls':len(r['tools']),'tool_arguments':[t['arguments'] for t in r['tools']],'http_status':200}
if not provider.provider_status()['configured']:
    raise SystemExit('Agnes API Key is not configured; no requests sent.')
for i in range(3):run('short_direct',f'short-{i+1}',short)
run('website_agent','single-player',lambda:agent('查询donk在2025年收录赛事的总图数、赛事数和来源文件，100字内回答并说明不是全年完整统计。'))
run('website_agent','two-player-comparison',lambda:agent('请比较donk和ZywOo在2025年收录赛事的Rating近似、地图数和MVP数，给出来源文件。200字内说明差异及数据覆盖限制。'))
report['summary']={}
for kind in ('short_direct','website_agent'):
    rows=[s for s in report['samples'] if s['kind']==kind];ok=[s['seconds'] for s in rows if s['success']]
    report['summary'][kind]={'attempts':len(rows),'successes':len(ok),'mean_seconds':round(statistics.mean(ok),3) if ok else None,'median_seconds':round(statistics.median(ok),3) if ok else None,'min_seconds':min(ok) if ok else None,'max_seconds':max(ok) if ok else None}
report['finished_at']=datetime.now(timezone.utc).isoformat();save();print(json.dumps({'summary':report['summary'],'report':str(TARGET)},ensure_ascii=True),flush=True)
