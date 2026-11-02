"""Check real image loading and warm navigation without request mocks (which disable cache)."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:7861/')
    parser.add_argument('--widths', default='1440,1000,390')
    parser.add_argument('--out', default='.planning/2026-11-02-cloud-agent-visibility/browser-local')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {'base': args.base, 'cases': []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width in [int(w) for w in args.widths.split(',')]:
            context = browser.new_context(viewport={'width': width, 'height': 960})
            # Retest the already-fixed Agent with previously off-screen coordinates.
            context.add_init_script("localStorage.setItem('swingaudit.floating.dragpos.v1', JSON.stringify({x:2103,y:737}))")
            page = context.new_page()
            errors, image_requests, image_responses = [], [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda req: image_requests.append(req.url) if '/atlas-arch.' in req.url else None)
            page.on('response', lambda res: image_responses.append({'status': res.status, 'headers': res.headers}) if '/atlas-arch.' in res.url else None)
            page.goto(args.base, wait_until='domcontentloaded', timeout=60000)
            if 'modelscope.cn/' in args.base:
                page.wait_for_selector('iframe[src*="ms.show"]', timeout=60000)
                page.frame_locator('iframe[src*="ms.show"]').locator('.atlas-plate img').wait_for(timeout=90000)
                app = next(frame for frame in page.frames if 'ms.show' in frame.url)
            else:
                app = page
            app.wait_for_function("() => {const i=document.querySelector('.atlas-plate img');return i?.complete && i.naturalWidth>0}", timeout=90000)
            initial = app.locator('.atlas-plate img').evaluate("i => ({url:i.currentSrc,width:i.naturalWidth,height:i.naturalHeight,animation:getComputedStyle(i).animationDuration})")
            assert initial['width'] == 1672 and initial['height'] == 941, initial
            assert initial['animation'] == '0.35s', initial
            app_width = app.evaluate('innerWidth')
            case = {'width': width, 'app_width': app_width, 'initial': initial, 'returns': []}
            initial_requests = len(image_requests)
            for route in ['/compare', '/verify', '/players']:
                app.evaluate('(route) => {location.hash = route}', route)
                app.locator('.atlas-plate img').wait_for(state='detached')
                result = app.evaluate("""() => new Promise(resolve => {
                    const started = performance.now();
                    const observer = new MutationObserver(() => {
                        const img = document.querySelector('.atlas-plate img');
                        if (!img) return;
                        observer.disconnect();
                        requestAnimationFrame(() => requestAnimationFrame(() => resolve({
                            ms: performance.now()-started, complete: img.complete,
                            naturalWidth: img.naturalWidth,
                            animation: getComputedStyle(img).animationName,
                            opacity: Number(getComputedStyle(img).opacity),
                            routeAnimation: getComputedStyle(document.querySelector('.tactical-lines path.t')).animationName,
                            warm: img.parentElement.classList.contains('is-warm')
                        })));
                    });
                    observer.observe(document.getElementById('root'), {childList:true,subtree:true});
                    location.hash = '/';
                })""")
                assert result['warm'] and result['complete'] and result['naturalWidth'] == 1672, result
                assert result['animation'] == 'none' and result['routeAnimation'] == 'none', result
                # ModelScope can keep a desktop-sized iframe even in a narrow host window.
                expected_opacity = 1 if app_width <= 860 else .55 if app_width <= 1180 else .94
                assert abs(result['opacity']-expected_opacity) < .01, result
                assert len(image_requests) == initial_requests, image_requests
                case['returns'].append({'from': route, **result})
            agent = app.locator('.floating-agent').evaluate("el => {const r=el.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,viewport:[innerWidth,innerHeight]}}")
            assert agent['x'] >= 0 and agent['right'] <= agent['viewport'][0]+1, agent
            assert agent['y'] >= 0 and agent['bottom'] <= agent['viewport'][1]+1, agent
            case['agent'] = agent
            app.locator('.atlas-hero').screenshot(path=str(out / f'home-return-{width}.png'))
            assert image_responses and 'immutable' in image_responses[0]['headers'].get('cache-control',''), image_responses
            assert not errors, errors
            case['image_requests'] = len(image_requests)
            case['image_headers'] = image_responses[0]['headers']
            case['errors'] = errors
            report['cases'].append(case)
            context.close()
        # Accessibility preference on initial entry, before any warm return.
        if '127.0.0.1' in args.base:
            context = browser.new_context(reduced_motion='reduce')
            page = context.new_page()
            page.goto(args.base, wait_until='domcontentloaded')
            page.locator('.atlas-plate img').wait_for(timeout=60000)
            assert page.locator('.atlas-plate img').evaluate('i => getComputedStyle(i).animationName') == 'none'
            report['reduced_motion'] = 'passed'
            context.close()
        browser.close()
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
