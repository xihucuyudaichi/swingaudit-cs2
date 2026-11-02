import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.planning/2026-11-01-agent-language-persistence'
report={'checks':[],'errors':[]}
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True);context=b.new_context();page=context.new_page()
 page.on('pageerror',lambda e:report['errors'].append(str(e)))
 def respond(route):
  body=route.request.post_data_json;route.fulfill(json={'answer':'## 回答\n保留内容：'+body['question'].split('问题：')[-1], 'tools':[], 'verification':{'passed':True,'checks':[]}})
 page.route('**/api/agent',respond)
 page.goto('http://127.0.0.1:5177/#/compare');page.wait_for_load_state('networkidle')
 agent=page.locator('.reading-agent');agent.get_by_role('textbox').fill('对比2026问题');agent.get_by_role('button',name='查询与分析',exact=True).click()
 expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题')
 page.clock.install();page.clock.fast_forward(600000);expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');report['checks'].append('idle_10_minutes')
 page.reload();expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');report['checks'].append('refresh_restore')
 page.get_by_role('link',name='赛事库',exact=True).first.click();page.get_by_role('link',name='选手对比',exact=True).first.click();expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');report['checks'].append('navigation_restore')
 page.get_by_label('研究年份',exact=True).select_option('2025');expect(agent.locator('.answer-markdown')).to_have_count(0)
 agent.get_by_role('textbox').fill('对比2025问题');agent.get_by_role('button',name='查询与分析',exact=True).click();expect(agent.locator('.answer-markdown')).to_contain_text('对比2025问题')
 page.reload();expect(page.get_by_label('研究年份',exact=True)).to_have_value('2025');expect(agent.locator('.answer-markdown')).to_contain_text('对比2025问题')
 page.get_by_label('研究年份',exact=True).select_option('2026');expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');report['checks'].append('year_isolation_and_restore')
 agent.locator('.agent-question-toggle').click();agent.get_by_role('textbox').fill('失败后草稿')
 page.unroute('**/api/agent');page.route('**/api/agent',lambda route:route.fulfill(status=502,json={'error':'模拟失败'}))
 agent.get_by_role('button',name='查询与分析',exact=True).click();expect(agent.get_by_role('alert')).to_contain_text('模拟失败');expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题')
 page.reload();expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');agent.locator('.agent-question-toggle').click();expect(agent.get_by_role('textbox')).to_have_value('失败后草稿');report['checks'].append('failure_preserves_answer_and_draft')
 page.unroute('**/api/agent');pending=[];page.route('**/api/agent',lambda route:pending.append(route))
 agent.get_by_role('button',name='查询与分析',exact=True).click();agent.get_by_role('button',name='取消分析',exact=True).click();expect(agent.locator('.answer-markdown')).to_contain_text('对比2026问题');report['checks'].append('cancel_preserves_answer')
 for route in pending:
  try:route.abort()
  except Exception:pass
 page.unroute_all(behavior='ignoreErrors')
 agent.get_by_role('button',name='清除对话',exact=True).click();page.reload();expect(agent.locator('.answer-markdown')).to_have_count(0);report['checks'].append('explicit_clear_persists')
 page.unroute('**/api/agent');page.route('**/api/agent',respond)
 page.goto('http://127.0.0.1:5177/#/verify');page.wait_for_load_state('networkidle');stage=page.locator('.verify-stage')
 for q in ['求证第一轮','求证第二轮']:
  stage.get_by_role('textbox').fill(q);stage.locator('form').evaluate('(form)=>form.requestSubmit()');expect(stage.locator('.answer-markdown')).to_contain_text(q)
 expect(stage.locator('.verify-turn-pills button')).to_have_count(2);stage.locator('.verify-turn-pills button').first.click();expect(stage.locator('.answer-markdown')).to_contain_text('求证第一轮')
 page.reload();expect(stage.locator('.verify-turn-pills button')).to_have_count(2);expect(stage.locator('.answer-markdown')).to_contain_text('求证第一轮');report['checks'].append('verify_turns_and_selection_restore')
 stage.get_by_role('button',name='清空对话',exact=True).click();page.reload();expect(stage.locator('.answer-markdown')).to_have_count(0);report['checks'].append('verify_clear_persists')
 page.goto('http://127.0.0.1:5177/#/compare');page.wait_for_load_state('networkidle');page.evaluate("localStorage.setItem('swingaudit.conversation.v1:#/compare:2026','broken json')");page.reload();expect(agent.get_by_role('textbox')).to_be_visible();report['checks'].append('corrupt_storage_safe')
 page.close()
 blocked=context.new_page();blocked.add_init_script("Storage.prototype.setItem = function(){throw new DOMException('full','QuotaExceededError')}")
 blocked.goto('http://127.0.0.1:5177/#/compare');expect(blocked.locator('.agent-storage-note')).to_contain_text('未能自动保存');report['checks'].append('storage_failure_visible');blocked.close();b.close()
assert not report['errors'],report['errors'];(OUT/'browser-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report))
