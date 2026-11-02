import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page()
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 health=page.request.get('http://127.0.0.1:5177/api/health').json()
 if not health.get('configured'):
  browser.close();print(json.dumps({'status':'skipped','reason':'The selected model provider is not configured'}));raise SystemExit(0)
 page.goto('http://127.0.0.1:5177/#/verify');page.get_by_label('需要核对的主张',exact=True).wait_for()
 page.get_by_label('需要核对的主张',exact=True).fill('请核对：donk在2025年收录赛事的地图数是多少？请从工具读取，给出来源文件和限制。')
 started=time.perf_counter()
 with page.expect_response(lambda r:r.url.endswith('/api/agent'),timeout=240000) as response:
  page.get_by_role('button',name='求证并查看来源',exact=True).click()
 res=response.value;answer=res.json();elapsed=round(time.perf_counter()-started,3)
 assert res.status==200,answer
 assert answer['model']==health['model'] and answer['tools'] and answer['answer']
 assert all(t['tool']=='query_research' and 'result' in t for t in answer['tools'])
 page.locator('.reading-agent .answer-markdown').wait_for();assert page.locator('.reading-agent .answer-markdown').inner_text().strip()
 assert not errors,errors
 out={'full_response_seconds':elapsed,'route':'/verify','http_status':res.status,'model':answer['model'],'tool_calls':len(answer['tools']),'browser_errors':errors,'response':answer}
 (ROOT/'verification/lab-agent-live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 browser.close();print(json.dumps({k:v for k,v in out.items() if k!='response'},ensure_ascii=True))
