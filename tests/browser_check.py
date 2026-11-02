from playwright.sync_api import sync_playwright
from pathlib import Path
import json
out=Path('verification');out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True)
 page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 routes=['/','/compare','/verify','/rankings','/scenarios','/players','/players/demo-player-03','/events','/events/demo-event-01','/library','/research']
 results=[]
 for width in [1440,390]:
  page.set_viewport_size({'width':width,'height':1000})
  for route in routes:
   page.goto('http://127.0.0.1:5177/#'+route);page.wait_for_load_state('networkidle')
   overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
   results.append({'route':route,'width':width,'overflow':overflow,'heading':page.locator('main').inner_text()[:60]})
   assert not overflow,(route,width)
  page.goto('http://127.0.0.1:5177/');page.wait_for_load_state('networkidle');page.screenshot(path=str(out/f'home-{width}.png'),full_page=True,animations='disabled')
 page.set_viewport_size({'width':1440,'height':1000})
 page.goto('http://127.0.0.1:5177/#/scenarios');page.get_by_role('button',name='运行推演',exact=True).click()
 assert page.locator('.flow-row').first.inner_text().find('ASTER')>=0
 page.get_by_role('button',name='另存情景',exact=True).click()
 page.goto('http://127.0.0.1:5177/#/research');page.reload();page.get_by_role('button',name='继续研究',exact=True).first.click()
 assert page.locator('.flow-row').count()==6
 page.locator('.scenario-change').nth(1).locator('select').nth(1).select_option('MVP')
 page.get_by_role('button',name='运行推演',exact=True).click();assert '只能有一位 MVP' in page.get_by_role('alert').inner_text()
 page.goto('http://127.0.0.1:5177/#/verify');page.get_by_role('button',name='开始求证',exact=True).click();page.locator('.verification-result').wait_for();assert page.locator('.claim-result').count()==2
 page.goto('http://127.0.0.1:5177/#/compare');page.get_by_role('button',name='2026 赛季').click();page.get_by_label('统计范围').select_option('grand_finals');page.get_by_role('button',name='应用条件').click();assert '缺少该范围' in page.locator('.paper').inner_text()
 page.locator('.stat-cell').first.click();assert page.get_by_role('dialog').is_visible();page.keyboard.press('Escape');assert page.get_by_role('dialog').count()==0
 page.screenshot(path=str(out/'compare-desktop.png'),full_page=True,animations='disabled')
 assert not errors,errors
 (out/'browser-results.json').write_text(json.dumps({'routes':results,'errors':errors,'flows':['scenario calculation','MVP conflict','save/reload/restore','claim verification','missing scope','evidence dialog escape']},ensure_ascii=False,indent=2),encoding='utf-8')
 b.close()
 print('PASS: 22 route/viewport checks + 6 interaction flows; no console errors')

