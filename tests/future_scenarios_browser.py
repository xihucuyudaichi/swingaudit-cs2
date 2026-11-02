"""Focused future-scenario flow checks; saved records are intercepted, no DB writes."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification'
report = {'viewports': [], 'flows': [], 'errors': []}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.on('pageerror', lambda error: report['errors'].append(str(error)))
    page.goto('http://127.0.0.1:5177/#/scenarios')
    page.wait_for_load_state('networkidle')
    page.get_by_label('未来赛事', exact=True).wait_for()
    options = page.get_by_label('未来赛事', exact=True).locator('option').all_text_contents()
    assert len(options) == 4 and not any('Cologne' in x for x in options)
    for width in (2215, 1440, 390):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), width
        report['viewports'].append(width)
        page.screenshot(path=str(OUT / f'future-scenarios-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 1000})
    assert page.get_by_label('队伍 1', exact=True).inner_text() == 'Vitality'
    assert page.get_by_label('队伍 3', exact=True).inner_text() == 'Falcons'
    page.get_by_label('选手 3', exact=True).select_option('ropz')
    assert page.get_by_label('队伍 3', exact=True).inner_text() == 'Vitality'
    page.get_by_label('队伍成绩 1', exact=True).select_option('冠军')
    assert page.get_by_label('队伍成绩 3', exact=True).input_value() == '冠军'
    page.get_by_label('队伍成绩 3', exact=True).select_option('四强')
    assert page.get_by_label('队伍成绩 1', exact=True).input_value() == '四强'
    page.get_by_label('选手 3', exact=True).select_option('m0nesy')
    assert page.get_by_label('队伍 3', exact=True).inner_text() == 'Falcons'
    assert page.get_by_label('队伍成绩 3', exact=True).input_value() == '未设定'
    page.get_by_role('button', name='＋ 添加选手', exact=True).click()
    assert page.get_by_label('队伍 4', exact=True).inner_text() == 'Vitality'
    assert page.get_by_label('队伍成绩 4', exact=True).input_value() == '四强'
    page.get_by_role('button', name='移除 flameZ', exact=True).click()
    report['flows'].append('automatic teams on initial selection/switch/add; teammate placement sync')
    page.get_by_label('Rating 2', exact=True).fill('1.60')
    page.get_by_label('图数 2', exact=True).fill('12')
    assert page.get_by_label('队伍 2', exact=True).inner_text() == 'Spirit'
    assert page.locator('.future-team input').count() == 0
    page.get_by_label('队伍成绩 2', exact=True).select_option('亚军')
    page.get_by_label('假设 MVP 得主', exact=True).select_option('donk')
    with page.expect_response('**/api/scenarios') as response:
        page.get_by_role('button', name='推演这条 If 线', exact=True).click()
    result = response.value.json()
    assert response.value.ok, result
    page.get_by_role('heading', name='如果这些假设成立', exact=True).wait_for()
    assert len(result['rows']) == page.locator('.future-result tbody tr').count()
    donk = next(x for x in result['rows'] if x['id'] == 'donk')
    assert donk['after_mvp'] == donk['before_mvp'] + 1
    assert donk['after_maps'] == donk['before_maps'] + 12
    report['flows'].append('single event with multiple players; MVP on runner-up; annual deltas')
    with page.expect_download() as dl:
        page.get_by_role('button', name='导出推演', exact=True).click()
    exported = json.loads(Path(dl.value.path()).read_text(encoding='utf-8'))
    assert exported == result
    report['flows'].append('JSON export preserves complete assumptions and result')
    saved = []
    def save(route):
        saved.append(route.request.post_data_json)
        route.fulfill(status=201, content_type='application/json', body=json.dumps({'id':'scenario-test','title':'测试未来线','created_at':'2026-11-01',**route.request.post_data_json}, ensure_ascii=False))
    page.route('**/api/records', save)
    page.locator('.future-result').get_by_role('button', name='保存研究', exact=True).click()
    page.wait_for_timeout(200)
    assert saved and saved[0]['payload']['mode'] == 'future_events'
    payload = saved[0]['payload']
    page.unroute('**/api/records', save)
    page.route('**/api/records', lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps({'records': [{'id': 'test-future', 'title': '测试未来线', 'created_at': '2026-11-01', 'payload': payload}]}, ensure_ascii=False)))
    page.goto('http://127.0.0.1:5177/#/research');page.wait_for_load_state('networkidle')
    page.get_by_role('button', name='继续研究', exact=True).first.click()
    page.get_by_label('未来赛事', exact=True).wait_for()
    assert page.get_by_label('Rating 2', exact=True).input_value() == '1.60'
    assert page.get_by_label('假设 MVP 得主', exact=True).input_value() == 'donk'
    assert page.get_by_label('队伍 2', exact=True).inner_text() == 'Spirit'
    assert page.locator('.future-result').count() == 0
    report['flows'].append('save and restore assumption parameters with mock persistence')
    page.get_by_role('button', name='＋ 添加一站', exact=True).click()
    page.get_by_label('未来赛事', exact=True).select_option('pgl-major-singapore-2026')
    page.get_by_label('假设 MVP 得主', exact=True).select_option('donk')
    with page.expect_response('**/api/scenarios') as response:
        page.get_by_role('button', name='推演这条 If 线', exact=True).click()
    result = response.value.json()
    assert response.value.ok, result
    assert len(result['assumption_manifest']) == 2
    donk = next(x for x in result['rows'] if x['id'] == 'donk')
    assert donk['after_mvp'] == donk['before_mvp'] + 2
    page.screenshot(path=str(OUT / 'future-scenarios-result.png'), full_page=True)
    page.get_by_label('Rating 1', exact=True).fill('1.62')
    assert page.locator('.future-result').count() == 0
    report['flows'].append('multi-event accumulation; edits invalidate stale results')
    page.get_by_label('研究年份', exact=True).select_option('2025')
    page.get_by_role('heading', name='这一年的比赛已结束', exact=True).wait_for()
    assert page.get_by_role('button', name='推演这条 If 线', exact=True).count() == 0
    page.get_by_role('button', name='前往 2026 未来赛程', exact=True).click()
    page.get_by_label('未来赛事', exact=True).wait_for()
    page.get_by_label('未来赛事', exact=True).select_option('custom')
    page.get_by_label('赛事名称', exact=True).fill('自定义未来测试杯')
    page.get_by_label('开赛日期', exact=True).fill('2026-12-20')
    page.get_by_label('结束日期', exact=True).fill('2026-12-22')
    with page.expect_response('**/api/scenarios') as response:
        page.get_by_role('button', name='推演这条 If 线', exact=True).click()
    assert response.value.ok, response.value.json()
    report['flows'].append('past-year guard and custom future schedule')
    assert not report['errors'], report['errors']
    browser.close()
(OUT / 'future-scenarios-browser.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=True))
