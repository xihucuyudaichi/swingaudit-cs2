"""Whole-site API integration and persistence checks; no screenshots."""
import json
from pathlib import Path
import sqlite3
from urllib.parse import quote
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:5177/'
result={'routes':[],'flows':[],'errors':[]};created=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(channel='chrome',headless=True)
  context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
  page.on('pageerror',lambda e:result['errors'].append(str(e)))
  def capture(resp):
   if resp.url.endswith('/api/records') and resp.request.method=='POST' and resp.status==201:created.append(resp.json()['id'])
  page.on('response',capture)
  def visit(path):
   page.goto(BASE+'#'+path);page.wait_for_load_state('networkidle');page.locator('.site-header').wait_for();page.locator('main h1, main h2').first.wait_for()
  visit('/');data=page.request.get(BASE+'api/history').json();event=data['seasons']['2026']['events'][0]['name']
  # Verify Home page 8 refinements
  assert page.locator('.demo-strip').count()==0
  assert page.locator('[data-testid="atlas-water-background"] canvas').count()==1
  assert page.locator('.brand-sub').count()==0
  home_text=page.locator('main').inner_text()
  assert '近似' not in home_text
  assert '读懂每一回合' not in home_text
  assert '拨开面板迷雾' in home_text
  assert '当前焦点 · 2026 赛季' in home_text
  assert '2026 赛季 Top 10 焦点选手与荣誉面板' in home_text
  assert '62.96' in home_text and '44.79' in home_text and '44.21' in home_text
  assert '6 MVP' in home_text and '3 MVP' in home_text
  assert page.get_by_label('研究年份',exact=True).input_value()=='2026'
  page.get_by_role('button',name='2026 已结束赛事加权个人荣誉积分（19 站）',exact=True).click()
  assert 'IEM科隆MAJOR' in page.locator('.paper-zone').inner_text()
  page.get_by_role('button',name='Top 10 十维细分 Rating 矩阵',exact=True).click()
  assert '大型赛事淘汰赛 & Big Matches' in page.locator('.paper-zone').inner_text()
  page.get_by_role('button',name='Top 10 综合荣誉与核心面板',exact=True).click()
  # Verify switching metric on Home updates table header
  page.get_by_label('统计范围',exact=True).select_option('ct_side')
  assert 'CT 阵营实测 Rating' in page.locator('.paper-zone table thead').inner_text()
  page.get_by_label('统计范围',exact=True).select_option('overall')
  result['flows'].append('home 8 refinements: brand-sub, no demo-strip, 2026 default, no 近似, metric switch')
  paths=['/','/compare','/verify','/rankings','/scenarios','/players','/players/donk','/events','/events/'+quote(event,safe=''),'/library','/research','/live']
  for width in [1440,390]:
   page.set_viewport_size({'width':width,'height':1000})
   for path in paths:
    visit(path);text=page.locator('main').inner_text();assert text and '无法连接数据服务' not in text
    assert not any(t in text for t in ['ASTER','虚构选手','模拟回复','演示赛季']),path
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'),(width,path)
    result['routes'].append({'path':path,'width':width,'pass':True})
  page.set_viewport_size({'width':1440,'height':1000});visit('/compare')
  page.get_by_text('数据对比：两人在此范围内相差',exact=False).wait_for()
  cmp_text=page.locator('main').inner_text()
  for dev_term in ['后端计算差值','Percentile','CT 钢蓝侧','T 茜红侧','Ward 轮廓系数','PCA 坐标','五工具闭环核验','四层数据底座']:
   assert dev_term not in cmp_text,f'Unexpected developer jargon on /compare: {dev_term}'
  sub_single_line=page.evaluate('''() => {
    const el = document.querySelector('main .page-heading .heading-sub');
    if (!el) return false;
    const style = window.getComputedStyle(el);
    const lh = parseFloat(style.lineHeight) || 22;
    return el.getBoundingClientRect().height <= lh * 1.5;
  }''')
  assert sub_single_line,'Compare subtitle should render on a single line on desktop'
  page.get_by_label('研究年份',exact=True).select_option('2025')
  page.get_by_text('数据对比：两人在此范围内相差',exact=False).wait_for()
  page.get_by_role('button',name='查看证据 ↗',exact=True).first.click();assert 'if_sim_2025_events.xlsx' in page.locator('dialog[open]').inner_text();page.keyboard.press('Escape')
  page.get_by_label('统计范围',exact=True).select_option('grand_finals');page.get_by_text('当前筛选范围内暂无完整比赛记录',exact=False).wait_for()
  page.get_by_label('研究年份',exact=True).select_option('2026');page.get_by_label('统计范围',exact=True).select_option('overall');page.get_by_text('数据对比：两人在此范围内相差',exact=False).wait_for();
  page.get_by_label('研究年份',exact=True).select_option('2027');assert page.get_by_text('暂无可用数据',exact=True).is_visible()
  page.get_by_label('研究年份',exact=True).select_option('2024');page.get_by_label('统计范围',exact=True).select_option('vs_top5');page.get_by_text('数据对比：两人在此范围内相差',exact=False).wait_for()
  result['flows'].append('comparison API, user-facing copy, single-line subtitle, evidence, missing scope, missing year, year switching')
  page.get_by_role('button',name='保存研究',exact=True).click();page.get_by_text('已保存到「我的研究」',exact=True).wait_for()
  visit('/research');assert page.locator('.research-list article').count()>=1
  page.reload();page.wait_for_load_state('networkidle');page.get_by_role('button',name='继续研究',exact=True).first.click();page.get_by_label('研究年份',exact=True).wait_for();assert page.get_by_label('研究年份',exact=True).input_value()=='2024'
  independent=browser.new_context();other=independent.new_page();other.goto(BASE+'#/research');other.locator('.research-list article').first.wait_for();assert other.locator('.research-list article').count()>=1;independent.close()
  result['flows'].append('save, reload, restore and independent browser read server record')
  visit('/rankings')
  assert page.get_by_label('统计范围',exact=True).count() == 0, '统计范围 should be hidden on /rankings'
  page.get_by_label('研究年份',exact=True).select_option('2026')
  assert '年度综合评分构成说明' in page.locator('main section.paper .formula-banner').inner_text()
  first_ranks = [page.locator('main tbody tr').nth(i).locator('td').first.inner_text().strip() for i in range(5)]
  assert first_ranks == ['#1', '#2', '#3', '#4', '#5'], f'Expected sequential ranks #1..#5, got {first_ranks}'
  vrs_btn = page.get_by_role('button', name='Valve 全球战队官方积分榜 (50)', exact=True)
  vrs_btn.wait_for()
  vrs_btn.click()
  width_check = page.evaluate('''() => {
    const paper = document.querySelector('main section.paper');
    const noteSpan = document.querySelector('main section.paper .note > span');
    const bannerP = document.querySelector('main section.paper .formula-banner p');
    if (!paper || !noteSpan || !bannerP) return { ok: false };
    const pw = paper.getBoundingClientRect().width;
    const nw = noteSpan.getBoundingClientRect().width;
    const bw = bannerP.getBoundingClientRect().width;
    const cards = [...document.querySelectorAll('main section.paper .profile-stats > div')];
    const strongs = [...document.querySelectorAll('main section.paper .profile-stats strong')];
    const fs = strongs[0] ? parseFloat(window.getComputedStyle(strongs[0]).fontSize) : 99;
    const singleLine = strongs.every(el => {
      const lh = parseFloat(window.getComputedStyle(el).lineHeight) || 25;
      return el.getBoundingClientRect().height <= lh * 1.4;
    });
    const equalHeights = cards.length === 3 && Math.max(...cards.map(c => c.getBoundingClientRect().height)) - Math.min(...cards.map(c => c.getBoundingClientRect().height)) <= 2;
    return { ok: nw >= pw * 0.88 && bw >= pw * 0.88 && fs <= 22 && singleLine && equalHeights, pw, nw, bw, fs, singleLine, equalHeights };
  }''')
  assert width_check['ok'], f'Expected full-width note, formula-banner p and clean profile-stats cards on /rankings, got {width_check}'
  assert page.locator('main tbody tr').count() == 50
  assert 'MOUZ' in page.locator('main tbody').inner_text()
  assert '1959.0' in page.locator('main tbody').inner_text()
  page.get_by_role('button', name='亚洲赛区 Top 20 (20)', exact=True).click()
  assert page.locator('main tbody tr').count() == 20
  assert 'The MongolZ' in page.locator('main tbody').inner_text()
  assert '1553.0' in page.locator('main tbody').inner_text()
  assert 'TYLOO' in page.locator('main tbody').inner_text()
  assert 'Lynn Vision' in page.locator('main tbody').inner_text()
  page.get_by_role('button', name='2026 两届 Major 官方直邀名单 (64)', exact=True).click()
  assert page.locator('main tbody tr').count() == 64
  page.get_by_role('button', name='10月5日 Valve 月度原榜 (50)', exact=True).click()
  assert page.locator('main tbody tr').count() == 50
  assert '2046.2' in page.locator('main tbody').inner_text()
  page.get_by_role('button', name='全球总榜 Top 50 (50)', exact=True).click()
  page.get_by_label('研究年份',exact=True).select_option('2025')
  assert '2025 赛季 HLTV 年度 Top 20 官方榜单与赛场表现' in page.locator('main section.paper').inner_text()
  page.get_by_label('研究年份',exact=True).select_option('2026')
  page.get_by_role('button', name='综合评分与官方对照分析', exact=False).click()
  assert '综合评分体系与 HLTV 官方榜单对照验证' in page.locator('main section.paper').inner_text()
  page.get_by_role('button', name='不同评选方式准确度对比 (6)', exact=True).click()
  assert page.locator('main tbody tr').count() == 6
  page.get_by_role('button', name='2019–2025 历年预测准确度 (7)', exact=True).click()
  assert page.locator('main tbody tr').count() == 7
  page.get_by_role('button', name='历年榜单与 2026 实时追踪', exact=False).click()
  result['flows'].append('Valve VRS 2026-11-01 latest global top 50, 2026 formula banner, 2025 official consistency, and top-level validation mode verified')
  for check_path in ['/rankings','/scenarios','/players','/players/donk','/events','/library']:
   visit(check_path)
   sub_ok=page.evaluate('''() => {
     const el = document.querySelector('main .page-heading .heading-sub');
     if (!el) return false;
     const style = window.getComputedStyle(el);
     const lh = parseFloat(style.lineHeight) || 22;
     return el.getBoundingClientRect().height <= lh * 1.5;
   }''')
   assert sub_ok,f'Subtitle should be single-line on desktop for {check_path}'
   body_txt=page.locator('main').inner_text()
   for bad in ['后端重算','Leave-One-Feature-Out','Spearman','baseline.xlsx','ektarr','SHA256','StandardScaler','KMeans','源选手ID','Jamie-Packer','eshtiakferdousmahi','Ageha6912','原始记录行级溯源','排雷记录']:
    assert bad not in body_txt,f'Unexpected developer jargon on {check_path}: {bad}'
  result['flows'].append('5 pages single-line subtitles and user-facing copy verified')
  visit('/scenarios');page.get_by_label('研究年份',exact=True).select_option('2026')
  page.get_by_label('未来赛事',exact=True).wait_for()
  page.get_by_label('假设 MVP 得主',exact=True).select_option('donk')
  page.get_by_role('button',name='推演这条 If 线',exact=True).click()
  page.get_by_role('heading',name='如果这些假设成立',exact=True).wait_for()
  assert page.locator('.future-result tbody tr').count() > 20
  with page.expect_download() as download:page.get_by_role('button',name='导出推演',exact=True).click()
  assert download.value.suggested_filename.endswith('.json')
  page.get_by_label('Rating 1',exact=True).fill('1.62');assert page.locator('.future-result').count()==0
  result['flows'].append('future event append-only scenario, full candidate rows, export and stale result invalidation')
  visit('/players');page.get_by_label('研究年份',exact=True).select_option('2024');page.get_by_label('搜索选手',exact=True).fill('Lucky');assert page.locator('tbody tr').count()==2
  result['flows'].append('ambiguous same-name identities remain separate')
  visit('/library');assert '尚不完整' in page.locator('main').inner_text();assert page.locator('tbody tr').count()>=35
  page.route('**/api/bootstrap',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"integration-test-offline"}'))
  page.reload(wait_until='domcontentloaded');page.get_by_text('无法连接数据服务',exact=True).wait_for();assert page.get_by_text('无法连接数据服务',exact=True).is_visible();assert page.locator('main tbody tr').count()==0
  result['flows'].append('backend failure shows error without synthetic fallback')
  assert not result['errors'],result['errors'];browser.close()
finally:
 if created:
  with sqlite3.connect(ROOT/'data/research.sqlite3') as db:
   for id in created:db.execute('DELETE FROM records WHERE id=?',(id,))
 (ROOT/'verification/connected-browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'routes':len(result['routes']),'flows':result['flows'],'errors':result['errors']},ensure_ascii=True))
