"""Assistant reading UX regression with deterministic HTTP responses; no model calls."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.planning/2026-11-01-agent-reading'
MARKDOWN = """## 结论
**donk 与 ZywOo 各有所长**，需要结合场上职责阅读数据。

### 关键数据
| 选手 | Rating | 样本图数 | 限制 |
| --- | ---: | ---: | --- |
| donk | 1.41 | 147 | 收录赛事 |
| ZywOo | 1.40 | 155 | 收录赛事 |

- 比较同一统计范围。
- 保留数据来源。

> 数据缺失不代表表现差。

[来源](https://example.com/evidence) [不安全链接](javascript:alert(1))
<script>window.injected = true</script>

```text
Rating = weighted mean
```
""" + '\n\n'.join('### 补充说明 %d\n\n这是用于验证长回答阅读的测试文本，真实数据应以来源为准。' % i for i in range(30))
REPLY = {'answer': MARKDOWN, 'tools': [{'arguments': {'query': 'donk'}, 'result': {'results': []}, 'tool': 'query_research'}], 'plan': {'task_label': '应被移除的分析主题'}, 'verification': {'passed': False, 'checks': [{'check_id': 'x', 'passed': False, 'label': '来源检查', 'detail': '测试待核对状态'}]}}
report = {'viewports': [], 'errors': []}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
    for width, height in [(2215,1244),(1440,1000),(390,844),(1440,620)]:
        page = context.new_page();page.set_viewport_size({'width': width, 'height': height})
        page.on('pageerror', lambda e: report['errors'].append(str(e)))
        page.route('**/api/agent', lambda route: route.fulfill(json=REPLY))
        page.goto('http://127.0.0.1:5177/#/compare');page.wait_for_load_state('networkidle')
        agent=page.locator('.reading-agent');field=agent.get_by_role('textbox')
        field.fill('测试对比与 Markdown 阅读');field.press('Control+Enter')
        expect(agent.locator('.answer-markdown h2')).to_have_text('结论')
        expect(field).to_have_count(0)
        expect(agent.locator('.answer-markdown strong').first).to_have_text('donk 与 ZywOo 各有所长')
        expect(agent.locator('.answer-markdown table')).to_have_count(1)
        expect(agent.locator('.answer-markdown li')).to_have_count(2)
        expect(agent.get_by_text('应被移除的分析主题')).to_have_count(0)
        assert agent.locator('script').count()==0 and not page.evaluate('Boolean(window.injected)')
        assert agent.locator('a[href^="javascript:"]').count()==0
        assert not agent.locator('.agent-evidence').evaluate('(e)=>e.open')
        dims=agent.evaluate('(e)=>({height:e.clientHeight,body:e.querySelector(".agent-reading-scroll").clientHeight,content:e.querySelector(".agent-reading-scroll").scrollHeight})')
        assert dims['content']>dims['body'] and dims['body']>=120,dims
        if height>650 and width>1180: assert dims['height']<=height-104,dims
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        agent.locator('.agent-reading-scroll').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        agent.locator('.agent-evidence summary').click()
        expect(agent.get_by_text('部分内容仍需核对',exact=True)).to_be_visible()
        agent.locator('.agent-reading-scroll').evaluate('(e)=>e.scrollTop=0')
        agent.get_by_role('button',name='展开阅读 ↗').click()
        dialog=page.get_by_role('dialog',name='分析结论展开阅读')
        expect(dialog).to_be_visible();expect(dialog.locator('.answer-markdown table')).to_have_count(1)
        assert dialog.bounding_box()['width']<=width
        page.screenshot(path=str(OUT/f'reader-{width}-{height}.png'))
        page.keyboard.press('Escape');expect(dialog).not_to_be_visible()
        expect(agent.get_by_role('button',name='展开阅读 ↗')).to_be_focused()
        assert page.evaluate('document.body.style.overflow') != 'hidden'
        agent.get_by_role('button',name='复制正文').click()
        expect(agent.get_by_text('已复制',exact=True)).to_be_visible()
        assert 'donk 与 ZywOo 各有所长' in page.evaluate('navigator.clipboard.readText()')
        bounds=agent.bounding_box();actions=agent.locator('.agent-result-actions').bounding_box()
        assert actions['y']+actions['height'] <= bounds['y']+bounds['height']+1
        saved=[]
        def save_mock(route):
            data=route.request.post_data_json;saved.append(data);route.fulfill(json={'id':'reading-check-only',**data})
        page.route('**/api/records',save_mock)
        agent.get_by_role('button',name='保存研究',exact=True).click()
        expect(page.get_by_text('已保存到「我的研究」',exact=True)).to_be_visible()
        assert saved[0]['payload']['question']=='测试对比与 Markdown 阅读' and saved[0]['payload']['result']['answer']==MARKDOWN
        agent.screenshot(path=str(OUT/f'panel-{width}-{height}.png'))
        agent.locator('.agent-question-toggle').click()
        expect(agent.get_by_role('textbox')).to_have_value('测试对比与 Markdown 阅读')
        report['viewports'].append({'width':width,'height':height,**dims})
        page.close()
    # Failure, cancellation and timeout must preserve the question and allow retry.
    page=context.new_page();page.on('pageerror',lambda e:report['errors'].append(str(e)))
    page.goto('http://127.0.0.1:5177/#/verify');page.wait_for_load_state('networkidle')
    agent=page.locator('.reading-agent');field=agent.get_by_role('textbox');field.fill('故障后保留的问题')
    page.route('**/api/agent',lambda route:route.fulfill(status=502,json={'error':'测试服务暂时不可用'}))
    agent.get_by_role('button',name='求证并查看来源',exact=True).click()
    expect(agent.get_by_role('alert')).to_have_text('测试服务暂时不可用');expect(field).to_have_value('故障后保留的问题')
    page.unroute_all();pending=[];page.route('**/api/agent',lambda route:pending.append(route))
    agent.get_by_role('button',name='求证并查看来源',exact=True).click();agent.get_by_role('button',name='取消分析',exact=True).click()
    expect(agent.get_by_role('alert')).to_contain_text('已取消');expect(field).to_be_enabled()
    page.clock.install();agent.get_by_role('button',name='求证并查看来源',exact=True).click();page.clock.fast_forward(120001)
    expect(agent.get_by_role('alert')).to_contain_text('超时');expect(field).to_be_enabled()
    for route in pending:
        try:route.abort()
        except Exception:pass
    page.unroute_all(behavior='ignoreErrors');page.close();browser.close()
assert not report['errors'],report['errors']
report['failure_cancel_timeout']=True
(OUT/'browser-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
