import json,time,sys
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
out={}
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:5177/#/compare');page.wait_for_load_state('networkidle')
 field=page.get_by_label('分析问题',exact=True);expect(field).to_be_visible()
 button=page.get_by_role('button',name='查询与分析',exact=True)
 pending_routes=[]
 page.route('**/api/agent',lambda route:pending_routes.append(route))
 button.click();page.get_by_role('button',name='取消分析',exact=True).click()
 expect(button).to_be_enabled();expect(page.get_by_role('alert')).to_contain_text('已取消')
 out['cancel_restores_form']=True;print('cancel: passed',flush=True)
 page.clock.install();button.click();page.clock.fast_forward(120001)
 expect(button).to_be_enabled();expect(page.get_by_role('alert')).to_contain_text('超时')
 out['timeout_restores_form']=True;print('timeout: passed',flush=True)
 for route in pending_routes:
  try: route.abort()
  except Exception: pass
 page.unroute_all(behavior="ignoreErrors");page.close();print("mock page closed",flush=True)
 if '--offline' in sys.argv:
  browser.close();print(json.dumps(out),flush=True);sys.exit(0)
 page=browser.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:5177/#/compare');page.wait_for_load_state('networkidle')
 field=page.get_by_label('分析问题',exact=True);expect(field).to_be_visible()
 print("live request starting",flush=True)
 start=time.monotonic()
 with page.expect_response(lambda r:r.url.endswith('/api/agent'),timeout=125000) as response:
  page.get_by_role('button',name='查询与分析',exact=True).click()
 res=response.value;data=res.json()
 out.update({'status':res.status,'seconds':round(time.monotonic()-start,2),'tools':len(data.get('tools',[])),'answer_chars':len(data.get('answer','')),'verification':data.get('verification',{}).get('status'),'error':data.get('error'),'browser_errors':errors})
 Path('verification/agent-loading-fix-20261101.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out,ensure_ascii=True),flush=True)
 assert res.status==200,data.get('error')
 expect(page.locator('.message')).to_be_visible();expect(page.locator('.agent-question-toggle')).to_be_visible()
 assert not errors
 browser.close()
