from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:5177/#/live');page.get_by_role('button',name='donk ↗',exact=True).wait_for();page.get_by_role('button',name='donk ↗',exact=True).click();assert page.locator('tbody tr').count()>10
 page.get_by_role('button',name='模型与回测',exact=True).click();assert '5.65' in page.locator('main').inner_text()
 page.set_viewport_size({'width':390,'height':900});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.screenshot(path='verification/live-mobile.png',full_page=True,animations='disabled')
 assert not errors,errors
 b.close();print('PASS historical player detail/model/mobile; no page errors')
