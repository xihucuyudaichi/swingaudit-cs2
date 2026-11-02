"""Check that home-page questions reach both verify inputs without losing history."""

import json
import re

from playwright.sync_api import expect, sync_playwright


BASE = 'http://127.0.0.1:5177/'
PREVIOUS_ANSWER = 'Previous verify answer'
CUSTOM_QUESTION = '请比较 ZywOo 和 donk 对阵强队时的表现。'


def main():
    checks = []
    errors = []
    agent_requests = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 2215, 'height': 1600})
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: agent_requests.append(request.url)
                if request.method == 'POST' and '/api/agent' in request.url else None)
        try:
            page.goto(BASE + '#/')
            page.wait_for_load_state('networkidle')
            expect(page.locator('.query-quick-tags button')).to_have_count(4)
            print('Home loaded', flush=True)
            page.evaluate('''() => {
              const turn = {question: 'Previous claim', answer: 'Previous verify answer', tools: [], year: '2026'};
              localStorage.setItem('swingaudit.conversation.v1:verify:2026',
                JSON.stringify({version: 1, data: {q: 'Old draft', turns: [turn], activeTurnIdx: 0}}));
              localStorage.setItem('swingaudit.conversation.v1:#/verify:2026',
                JSON.stringify({version: 1, data: {q: 'Old agent draft', result: turn}}));
            }''')

            def home():
                page.locator('.brand').click()
                expect(page).to_have_url(re.compile(r'#/$'))
                expect(page.locator('.query-quick-tags button')).to_have_count(4)

            def verify_question(expected):
                expect(page).to_have_url(re.compile(r'#/verify$'))
                expect(page.get_by_label('待核实的社区争议主张')).to_have_value(expected)
                expect(page.locator('.reading-agent textarea')).to_have_value(expected)
                expect(page.locator('.verify-stage .answer-markdown')).to_contain_text(PREVIOUS_ANSWER)

            for index in range(4):
                if index:
                    home()
                button = page.locator('.query-quick-tags button').nth(index)
                selected = button.evaluate('(element) => element.textContent.slice(2)')
                button.click()
                verify_question(selected)
                checks.append('example_%d' % (index + 1))
                print('Example %d passed' % (index + 1), flush=True)

            page.reload()
            expect(page.get_by_label('待核实的社区争议主张')).to_have_value(selected)
            expect(page.locator('.verify-stage .answer-markdown')).to_contain_text(PREVIOUS_ANSWER)
            checks.append('refresh_keeps_selected_question_and_history')
            print('Refresh passed', flush=True)

            home()
            button = page.locator('.query-quick-tags button').nth(3)
            button.click()
            verify_question(selected)
            checks.append('same_example_can_be_selected_again')
            print('Repeat selection passed', flush=True)

            home()
            page.get_by_label('首页研究问题').fill(CUSTOM_QUESTION)
            page.get_by_role('button', name='开始研究').click()
            verify_question(CUSTOM_QUESTION)
            checks.append('home_custom_question')
            print('Custom question passed', flush=True)

            claim = page.get_by_label('待核实的社区争议主张')
            claim.fill('Manually edited 2026 draft')
            home()
            page.get_by_role('link', name='言论求证', exact=True).first.click()
            expect(claim).to_have_value('Manually edited 2026 draft')
            checks.append('ordinary_navigation_does_not_reapply_old_question')
            print('Ordinary navigation passed', flush=True)

            page.get_by_label('研究年份', exact=True).select_option('2025')
            claim.fill('Separate 2025 draft')
            page.get_by_label('研究年份', exact=True).select_option('2026')
            expect(claim).to_have_value('Manually edited 2026 draft')
            expect(page.locator('.verify-stage .answer-markdown')).to_contain_text(PREVIOUS_ANSWER)
            checks.append('year_specific_draft_and_history_remain_isolated')

            assert not agent_requests, 'Selecting a question should not start an agent request'
            home()
            button = page.locator('.query-quick-tags button').nth(2)
            selected = button.evaluate('(element) => element.textContent.slice(2)')
            button.click()
            verify_question(selected)
            submitted = []

            def mock_agent(route):
                submitted.append(route.request.post_data_json)
                route.fulfill(json={'answer': 'Mocked verification answer', 'tools': [], 'year': '2026'})

            page.route('**/api/agent', mock_agent)
            page.locator('.verify-stage').get_by_role('button', name='核实主张并查看来源').click()
            expect(page.locator('.verify-stage .answer-markdown')).to_contain_text('Mocked verification answer')
            assert len(submitted) == 1 and submitted[0]['question'] == selected, submitted
            checks.append('explicit_submit_sends_selected_question_to_mock_agent')

            assert not errors, errors
            checks.append('no_automatic_agent_request_or_page_errors')
            print(json.dumps({'checks': checks, 'errors': errors}))
        finally:
            context.close()
            browser.close()


if __name__ == '__main__':
    main()
