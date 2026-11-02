"""End-to-end verification of the global contextual floating Agent, free dragging, and sculpted UI."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.planning/2026-11-01-floating-agent-context'
OUT.mkdir(parents=True, exist_ok=True)

report = {'routes_checked': [], 'drag_checks': [], 'context_payloads': [], 'errors': []}

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 960})
    page = context.new_page()
    page.on('pageerror', lambda e: report['errors'].append(str(e)))

    captured = []
    def handle_agent(route):
        body = route.request.post_data_json
        captured.append(body)
        ctx = body.get('context') or {}
        ans = (
            f"**结论：2026 年已收录数据里，{ctx.get('page_name', '当前页面')}焦点选手表现突出。**\n\n"
            f"### 关键数据（2026 已收录赛事，Rating 3.0 口径）\n\n"
            f"- **ZywOo**：全年 Rating 1.40，155 图，6 次 MVP、5 次 EVP；对前 5 强 1.33、超级精英赛事 1.53、大型赛事总决赛 1.44，荣誉分 62.96。\n"
            f"- **donk**（Spirit）：Rating 1.41，147 图，3 次 MVP、5 次 EVP；破点突破手同位置领先。\n"
            f"- **m0NESY**（Falcons）：Rating 1.30，142 图，1 MVP、7 EVP；IEM 科隆 Major MVP。\n\n"
            f"**已结合背景**：{ctx.get('selected_text') or ctx.get('page_summary') or '默认'}\n\n"
            f"### 限制\n\n"
            f"- 仅覆盖当前已收录的 2026 赛事快照，非全年完整统计。\n"
            f"- 角色标签是项目根据比赛录像与统计特征归纳的场上职责参考。"
        )
        route.fulfill(json={
            'answer': ans,
            'year': body.get('year', '2026'),
            'tools': [
                {'tool': 'query_research', 'controlled_tool': 'T1_multi_tier_query', 'arguments': {'year': '2026', 'query': 'donk', 'kind': 'players'}, 'result': {'results': []}},
                {'tool': 'query_research', 'controlled_tool': 'T1_multi_tier_query', 'arguments': {'year': '2026', 'query': 'ZywOo', 'kind': 'players'}, 'result': {'results': []}}
            ],
            'verification': {'passed': True, 'checks': []}
        })

    page.route('**/api/agent', handle_agent)

    # 1. Compare page: full-width layout + floating agent + player selection awareness
    page.goto('http://127.0.0.1:5177/#/compare')
    page.wait_for_load_state('networkidle')
    agent = page.locator('.reading-agent.floating-agent')
    expect(agent).to_be_visible()
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('选手对比')
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('donk vs ZywOo')
    page.screenshot(path=str(OUT / 'floating-compare-1440.png'))
    report['routes_checked'].append('/compare')

    # Click a role card on /compare to test click-based selection capture
    page.locator('.role-card').first.click()
    expect(agent.locator('.context-pill.selection-pill')).to_contain_text('页面点选')
    agent.locator('.agent-quick-chip.is-selection').click()
    agent.get_by_role('button', name='查询与分析', exact=True).click()
    expect(agent.locator('.answer-markdown')).to_contain_text('选手对比')
    assert captured[-1]['context']['page_name'] == '选手对比'
    assert captured[-1]['context']['selected_kind'] == '页面点选'
    assert 'donk' in captured[-1]['context']['selected_text']
    report['context_payloads'].append(captured[-1]['context'])
    agent.screenshot(path=str(OUT / 'panel-answer-close-up.png'))

    # 2. Test free pointer dragging of expanded floating card
    before_box = agent.bounding_box()
    header_box = agent.locator('.floating-drag-header').bounding_box()
    page.mouse.move(header_box['x'] + 80, header_box['y'] + 18)
    page.mouse.down()
    page.mouse.move(220, 160, steps=10)
    page.mouse.up()
    after_box = agent.bounding_box()
    assert after_box['x'] < 300 and after_box['y'] < 220, f"Expected dragged position near top-left, got {after_box}"
    report['drag_checks'].append({'panel_before': before_box, 'panel_after': after_box})
    page.screenshot(path=str(OUT / 'floating-dragged-compare.png'))

    # Reset dock position via double click on header and ensure dock left/right button is gone
    expect(agent.get_by_role('button', name='将悬浮窗移至左下角')).to_have_count(0)
    expect(agent.get_by_role('button', name='将悬浮窗移至右下角')).to_have_count(0)
    agent.locator('.floating-drag-header').dblclick()
    expect(agent).to_have_class('agent-panel reading-agent floating-agent has-answer')

    # 3. Test minimize to sculpted capsule pill & dragging the pill
    agent.get_by_role('button', name='收起悬浮窗').click()
    pill = page.locator('.floating-agent-pill')
    expect(pill).to_be_visible()
    pill.screenshot(path=str(OUT / 'pill-close-up.png'))
    pill_before = pill.bounding_box()
    page.mouse.move(pill_before['x'] + 40, pill_before['y'] + 20)
    page.mouse.down()
    page.mouse.move(480, 820, steps=8)
    page.mouse.up()
    pill_after = pill.bounding_box()
    assert abs(pill_after['x'] - pill_before['x']) > 100, f"Expected pill to drag horizontally, got {pill_before} -> {pill_after}"
    expect(pill).to_be_visible()  # Dragging pill must not accidentally expand it
    report['drag_checks'].append({'pill_before': pill_before, 'pill_after': pill_after})
    page.screenshot(path=str(OUT / 'floating-pill-minimized.png'))
    # Reset pos and click pill to expand
    pill.click()
    expect(agent).to_be_visible()
    agent.locator('.floating-drag-header').dblclick()

    # 4. Rankings page: VRS tab switch + table row click context
    page.goto('http://127.0.0.1:5177/#/rankings')
    page.wait_for_load_state('networkidle')
    page.get_by_role('button', name='Valve 全球战队官方积分榜 (50)', exact=True).click()
    page.get_by_role('button', name='亚洲赛区 Top 20 (20)', exact=True).click()
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('亚洲赛区 Top 20')
    page.locator('main tbody tr').first.click()
    expect(agent.locator('.context-pill.selection-pill')).to_contain_text('The MongolZ')
    page.screenshot(path=str(OUT / 'floating-rankings-row-selected.png'))
    agent.get_by_role('textbox').fill('解读我点选的这支战队在亚洲赛区的积分优势')
    agent.get_by_role('button', name='查询与分析', exact=True).click()
    expect(agent.locator('.answer-markdown')).to_contain_text('The MongolZ')
    assert '亚洲赛区 Top 20' in captured[-1]['context']['page_summary']
    assert 'The MongolZ' in captured[-1]['context']['selected_text']
    report['routes_checked'].append('/rankings')
    report['context_payloads'].append(captured[-1]['context'])

    # 5. Player detail page: /players/donk automatic focused_player + text selection
    page.goto('http://127.0.0.1:5177/#/players/donk')
    page.wait_for_load_state('networkidle')
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('选手档案 · donk')
    page.evaluate("""() => {
      const p = document.querySelector('main .player-profile .info-card p');
      if (p) {
        const range = document.createRange();
        range.selectNodeContents(p);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
      }
    }""")
    expect(agent.locator('.context-pill.selection-pill')).to_contain_text('划词选取')
    page.screenshot(path=str(OUT / 'floating-player-detail-text-selected.png'))
    agent.get_by_role('textbox').fill('他今年的这项位置表现说明了什么？')
    agent.get_by_role('button', name='查询与分析', exact=True).click()
    expect(agent.locator('.answer-markdown')).to_contain_text('选手档案 · donk')
    assert captured[-1]['context']['focused_player'] == 'donk'
    assert captured[-1]['context']['selected_kind'] == '划词选取'
    report['routes_checked'].append('/players/donk')
    report['context_payloads'].append(captured[-1]['context'])

    # 6. Scenarios page: If-line event & MVP context
    page.goto('http://127.0.0.1:5177/#/scenarios')
    page.wait_for_load_state('networkidle')
    page.get_by_label('假设 MVP 得主', exact=True).select_option('donk')
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('If 线推演')
    expect(agent.locator('.context-pill.page-pill')).to_contain_text('MVP donk')
    report['routes_checked'].append('/scenarios')

    browser.close()

assert not report['errors'], report['errors']
(OUT / 'floating-agent-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'routes_checked': report['routes_checked'], 'drag_checks': len(report['drag_checks']), 'payloads': len(report['context_payloads']), 'errors': report['errors']}, ensure_ascii=False))
