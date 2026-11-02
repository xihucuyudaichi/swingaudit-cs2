"""Compact, paginated discovery over the same data shown by the website."""
import re

ROLE_ALIASES = {'lurker':'自由', '自由人':'自由', 'awper':'主狙', 'sniper':'主狙', '狙击手':'主狙', '突破手':'突破', 'entry':'突破', 'support':'辅助'}


def question_scope(question, selected_year, page_context, data):
    years = set(re.findall(r'(?<!\d)(20\d{2})(?!\d)', question))
    years.update('20' + y for y in re.findall(r'(?<!\d)(\d{2})\s*年', question))
    year = next(iter(years)) if len(years) == 1 else str(selected_year)
    players = data.get('seasons', {}).get(year, {}).get('players', [])
    names = [p['name'] for p in players if re.search(r'(?<![a-z0-9])'+re.escape(p['name'])+r'(?![a-z0-9])',question,re.I)]
    referential = bool(re.search(
        r'这两[个位名人]|这俩|他们俩|当前选中|页面选中|这位选手|这名选手|该选手|他(?:在|的|今年|本赛季|为什么|怎么)|'
        r'本站|这场赛事|该赛事|当前页面|这页|这段|这行|选中|所选|当前榜|^(?:谁更强|对比一下|比较一下|怎么看|解读一下|分析一下|总结一下)[？?。!！]*$',
        question
    ))
    if not isinstance(page_context, dict): return year, []
    selected_text = str(page_context.get('selected_text') or '').strip()
    focused_player = str(page_context.get('focused_player') or '').strip()
    if not names and selected_text and not discovery_role(question):
        sel_names = [p['name'] for p in players if re.search(r'(?<![a-z0-9])'+re.escape(p['name'])+r'(?![a-z0-9])', selected_text, re.I)]
        if sel_names: return year, sel_names[:3]
    if not names and focused_player and (referential or not discovery_role(question)):
        fp_names = [p['name'] for p in players if p['id'].casefold() == focused_player.casefold() or p['name'].casefold() == focused_player.casefold()]
        if fp_names: return year, fp_names[:2]
    # Explicit names and open-ended role questions always outrank the page selection.
    if names or not referential: return year, []
    selected = page_context.get('selected_players')
    if not isinstance(selected,list): return year, []
    ids = {s.casefold() for s in selected[:2] if isinstance(s,str)}
    return year, [p['name'] for p in players if p['id'].casefold() in ids or p['name'].casefold() in ids]


def discovery_role(question):
    for word in ('自由人','主狙','狙击手','突破手','辅助'):
        if word in question: return word
    return ''


def search_site_data(data, role_report, args):
    year, kind = str(args['year']), args['kind']
    season = data['seasons'].get(year)
    if not season:
        return {'year':year,'missing':True,'reason':'该年份暂无已收录数据。','available_years':sorted(data['seasons'])}
    query = args.get('query','').strip().casefold()
    if query in ('all','全部','所有','*'): query=''
    role = args.get('role','').strip().casefold()
    if role in ('all','全部','所有'): role=''
    role = ROLE_ALIASES.get(role,role)
    limit,offset = args.get('limit',10),args.get('offset',0)
    roles = {p['id']:p for p in role_report.get('seasons',{}).get(year,{}).get('players',[])}
    results=[]
    if kind == 'players':
        for p in season['players']:
            rp=roles.get(p['id'],{})
            role_label=rp.get('role_short') or rp.get('role_name') or ''
            if role and role not in role_label.casefold(): continue
            if query and query not in ' '.join(str(p.get(k) or '') for k in ('id','name','team')).casefold(): continue
            if (p.get('maps') or 0) < args.get('min_maps',0): continue
            rows=p.get('events') or []
            evidence=[]
            for row in rows:
                source={k:row.get(k) for k in ('source_file','source_url','sheet') if row.get(k)}
                if source and source not in evidence: evidence.append(source)
                if len(evidence)>=2: break
            benchmarks=((p.get('multi_tier_benchmarks') or {}).get('blum_2026') or {})
            results.append({'id':p['id'],'name':p['name'],'year':year,'team':p.get('team'),'role':role_label or '未收录',
                'rating_estimate':p.get('rating_estimate'),'maps':p.get('maps'),'mvp':p.get('mvp'),'evp':p.get('evp'),
                'weighted_honor_score':p.get('weighted_honor_score'),
                'vs_top5':(benchmarks.get('vs_top5') or {}).get('rating',(p.get('opponents') or {}).get('vsTop5')),
                'big_playoffs':(benchmarks.get('big_playoffs') or {}).get('rating'),
                'source':evidence,'detail_query':p['name']})
        order=args.get('sort_by','rating')
        field={'rating':'rating_estimate','honor':'weighted_honor_score','maps':'maps'}.get(order)
        if field:results.sort(key=lambda p:(p.get(field) is None,-(p.get(field) or 0),p['name'].casefold()))
        else:results.sort(key=lambda p:p['name'].casefold())
    else:
        for event in season['events']:
            if query and query not in ' '.join(str(event.get(k) or '') for k in ('name','name_zh','tier')).casefold():continue
            results.append({k:event.get(k) for k in ('name','name_zh','year','tier','period_start','period_end','weight_label','source_url')})
        results.sort(key=lambda p:(str(p.get('period_start') or ''),p['name']))
    total=len(results)
    return {'year':year,'kind':kind,'query':query,'role_filter':role,'sort_by':args.get('sort_by','rating'),
        'scanned_count':len(season[kind]),'total_matches':total,'offset':offset,'limit':limit,
        'next_offset':offset+limit if offset+limit<total else None,'results':results[offset:offset+limit],
        'available_years':sorted(data['seasons']),
        'missing':total==0,'reason':'当前条件下未匹配到记录，不代表现实中不存在。' if not total else None,
        'notice':'已检索该年份全库，再按条件排序分页。角色标签是项目对打法的近似判断，可能有误分，不等于官方认证；不能把单项排序或当前库覆盖称为世界权威排名。按detail_query可继续查选手完整记录，存在next_offset时可翻页。'}
