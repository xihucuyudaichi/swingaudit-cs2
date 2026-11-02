import React, { useEffect, useRef, useState } from 'react';
import './scenarios.css';

export default function FutureScenarios({ context, ui }) {
  const { year, setYear, season, restored } = context;
  const { Heading, Note, Table, Save, api, exportFile, f } = ui;
  const saved = restored?.mode === 'future_events' ? restored : null;
  const [catalog, setCatalog] = useState(null);
  const [events, setEvents] = useState(saved?.events || []);
  const [active, setActive] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const req = useRef(null);
  const asOf = catalog?.as_of || new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date());
  const players = (season?.players || []).map(p => {
    const rows = p.events.filter(r => r.period_end && r.period_end < asOf && typeof r.rating === 'number' && r.maps > 0);
    const maps = rows.reduce((n, r) => n + r.maps, 0);
    const team = p.team?.trim() || [...rows].sort((a, b) => b.period_end.localeCompare(a.period_end)).find(r => r.team?.trim())?.team?.trim() || '';
    return { ...p, team, maps, rating_estimate: maps ? rows.reduce((n, r) => n + r.rating * r.maps, 0) / maps : null };
  }).filter(p => p.maps > 0);
  const playerById = Object.fromEntries(players.map(p => [p.id, p]));
  const options = (catalog?.events || []).filter(e => e.start_date.startsWith(year));
  const futureYear = catalog?.as_of.slice(0, 4);
  const eligible = futureYear === year && players.length > 0;
  const current = events[active];
  const metadata = current?.event_id === 'custom' ? current : options.find(e => e.id === current?.event_id);
  const delta = n => n > 0 ? `+${f(n, 3)}` : f(n, 3);
  useEffect(() => {
    context.setUiContext?.(prev => ({
      ...prev,
      scenarioEvent: metadata?.name || current?.name || current?.event_id || '',
      scenarioMvp: playerById[current?.mvp_player]?.name || current?.mvp_player || '',
      scenarioPlayers: (current?.players || []).slice(0, 4).map(p => `${playerById[p.player_id]?.name || p.player_id}(Rating ${p.rating}, ${p.maps}图)`).join('、')
    }));
  }, [year, active, events, catalog]);

  function seedPlayer(p) {
    return { player_id: p.id, rating: Number(p.rating_estimate ?? 1).toFixed(2), maps: '10', team: p.team, team_place: '未设定', evp: false };
  }
  function seedEvent(id = options[0]?.id || 'custom') {
    return { event_id: id, name: '', start_date: '', end_date: '', tier: '大型赛事', mvp_player: '', players: players.slice(0, 3).map(seedPlayer) };
  }
  useEffect(() => {
    const c = new AbortController();
    api('upcoming-events', undefined, c.signal).then(data => {
      setCatalog(data);
      setEvents(bindTeams(saved?.events || [seedEvent(data.events.find(e => e.start_date.startsWith(year))?.id || 'custom')]));
    }).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => { c.abort(); req.current?.abort(); };
  }, []);

  function reset() { req.current?.abort(); req.current = null; setResult(null); setError(''); setBusy(false); }
  function bindTeams(items) {
    return items.map(event => {
      const rows = event.players.map(p => ({ ...p, team: playerById[p.player_id]?.team || '' }));
      const placements = new Map();
      for (const p of rows) {
        const key = p.team.toLowerCase();
        if (key && p.team_place !== '未设定' && !placements.has(key)) placements.set(key, p.team_place);
      }
      return { ...event, players: rows.map(p => ({ ...p, team_place: placements.get(p.team.toLowerCase()) || '未设定' })) };
    });
  }
  function update(next) { reset(); setEvents(bindTeams(next)); }
  function patchEvent(patch) { update(events.map((e, i) => i === active ? { ...e, ...patch } : e)); }
  function patchPlayer(index, patch) {
    const team = current.players[index].team.toLowerCase();
    patchEvent({ players: current.players.map((p, i) => i === index || (patch.team_place !== undefined && team && p.team.toLowerCase() === team) ? { ...p, ...patch } : p) });
  }
  async function run(e) {
    e.preventDefault(); reset();
    const c = new AbortController(); req.current = c; setBusy(true);
    try {
      const payload = { mode: 'future_events', year, events: events.map(e => ({ ...e, players: e.players.map(p => ({ ...p, rating: p.rating === '' ? null : Number(p.rating), maps: p.maps === '' ? null : Number(p.maps) })) })) };
      const response = await api('scenarios', payload, c.signal);
      if (req.current === c) setResult(response);
    } catch (err) { if (err.name !== 'AbortError' && req.current === c) setError(err.message); }
    finally { if (req.current === c) setBusy(false); }
  }

  return <>
    <Heading title="If 线推演：下一站，会改变什么？" subtitle="为尚未开赛的赛事设定选手发挥与 MVP 归属，比较不同未来下的年度表现和排名。" />
    <div className="scope-bar future-scope">
      <label>研究年份 <select aria-label="研究年份" value={year} onChange={e => setYear(e.target.value)}>{Array.from({ length: 15 }, (_, i) => String(2026 - i)).map(y => <option key={y}>{y}</option>)}</select></label>
      <span>未来赛事沙盘 · {catalog ? `以 ${catalog.as_of} 为起点` : '正在读取赛程…'}</span>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {!catalog ? <section className="paper"><p>正在读取未来赛程…</p>{error && <button className="btn" onClick={() => location.reload()}>重新加载</button>}</section> : !eligible ?
      <section className="paper"><h2>这一年的比赛已结束</h2><p>If 线从当前日期向未来推演。切回 {futureYear}，再设定下一站的表现。</p><button className="btn primary" onClick={() => setYear(futureYear)}>前往 {futureYear} 未来赛程</button></section> :
      <section className="paper future-paper">
        {restored?.type === 'scenario' && !saved && <Note>这份收藏使用旧版历史改写规则。已保留原收藏，请在下方重新建立未来赛事假设。</Note>}
        <div className="future-intro"><div><span className="future-kicker">FUTURE SCENARIOS / 01</span><h2>已发生的留在原处，接下来的由你设想。</h2></div><p>历史成绩固定 → 加入未来表现 → 对比年度变化</p></div>
        <div className="future-stations" aria-label="推演赛事列表">
          {events.map((e, i) => <button type="button" className={'future-station ' + (i === active ? 'selected' : '')} aria-pressed={i === active} key={i} onClick={() => setActive(i)}><span>0{i + 1}</span>{e.event_id === 'custom' ? e.name || '自定义未来赛事' : options.find(x => x.id === e.event_id)?.name || '赛程已过期'}<small>{e.players.length} 位假设参赛 · MVP {playerById[e.mvp_player]?.name || '未设定'}</small></button>)}
          <button type="button" className="btn" disabled={events.length >= 8} onClick={() => { const id = options.find(o => !events.some(e => e.event_id === o.id))?.id || 'custom'; update([...events, seedEvent(id)]); setActive(events.length); }}>＋ 添加一站</button>
        </div>
        {current && <form onSubmit={run}>
          <div className="future-event-head"><h3>01 / 选择未开赛赛事</h3>{events.length > 1 && <button className="text-link" type="button" onClick={() => { update(events.filter((_, i) => i !== active)); setActive(Math.max(0, active - 1)); }}>移除本站</button>}</div>
          <div className="future-event-fields">
            <label className="field">未来赛事<select aria-label="未来赛事" value={current.event_id} onChange={e => patchEvent({ event_id: e.target.value })}>
              {!options.some(e => e.id === current.event_id) && current.event_id !== 'custom' && <option value={current.event_id}>该赛事已开赛或不再收录，请重新选择</option>}
              {options.map(e => <option key={e.id} value={e.id} disabled={events.some((x, i) => i !== active && x.event_id === e.id)}>{e.name}</option>)}<option value="custom">自定义未来赛事（假设赛程）</option>
            </select></label>
            {current.event_id !== 'custom' && <div className="future-date"><b>{metadata?.start_date} — {metadata?.end_date}</b><span>{metadata?.tier} · 尚未开赛</span>{metadata?.source_url && <a href={metadata.source_url} target="_blank" rel="noreferrer">主办方赛程 ↗</a>}</div>}
          </div>
          {current.event_id === 'custom' && <div className="future-custom">
            <label className="field">赛事名称<input aria-label="赛事名称" required maxLength={100} value={current.name} onChange={e => patchEvent({ name: e.target.value })} placeholder="为假设中的未来赛事命名" /></label>
            <label className="field">开赛日期<input aria-label="开赛日期" type="date" required min={catalog.as_of} max={`${year}-12-31`} value={current.start_date} onChange={e => patchEvent({ start_date: e.target.value })} /></label>
            <label className="field">结束日期<input aria-label="结束日期" type="date" required min={current.start_date || catalog.as_of} max={`${year}-12-31`} value={current.end_date} onChange={e => patchEvent({ end_date: e.target.value })} /></label>
            <label className="field">赛事级别<select aria-label="赛事级别" value={current.tier} onChange={e => patchEvent({ tier: e.target.value })}>{catalog.tiers.map(t => <option key={t}>{t}</option>)}</select></label>
          </div>}
          {metadata?.schedule_note && <p className="future-caption">{metadata.schedule_note}</p>}
          <div className="future-event-head"><h3>02 / 设定各位选手的发挥</h3><button type="button" className="btn" disabled={current.players.length >= players.length} onClick={() => { const p = players.find(p => !current.players.some(x => x.player_id === p.id)); if (p) patchEvent({ players: [...current.players, seedPlayer(p)] }); }}>＋ 添加选手</button></div>
          <p className="future-caption">以下为假设参赛名单，并非官方报名表。初始 Rating 沿用收录赛事均值，10 图为可修改的起始假设；未添加的选手保持现有成绩。队伍按已收录资料自动匹配，同队成绩联动。</p>
          <div className="future-player-scroll"><table className="future-player-table"><thead><tr><th>假设参赛选手</th><th>赛事 Rating</th><th>参赛图数</th><th>所属队伍 / 假设成绩</th><th>EVP</th><th><span className="sr-only">操作</span></th></tr></thead><tbody>
            {current.players.map((p, i) => <tr key={p.player_id}>
              <td><select aria-label={`选手 ${i + 1}`} value={p.player_id} onChange={e => { const id = e.target.value; patchEvent({ mvp_player: current.mvp_player === p.player_id ? '' : current.mvp_player, players: current.players.map((x, j) => j === i ? seedPlayer(playerById[id]) : x) }); }}>{players.map(x => <option key={x.id} value={x.id} disabled={current.players.some((r, j) => j !== i && r.player_id === x.id)}>{x.name}</option>)}</select><small>收录赛事均值 {f(playerById[p.player_id]?.rating_estimate)}</small></td>
              <td><input aria-label={`Rating ${i + 1}`} required type="number" min="0" max="3" step="0.01" value={p.rating} onChange={e => patchPlayer(i, { rating: e.target.value })} /></td>
              <td><input aria-label={`图数 ${i + 1}`} required type="number" min="1" max="50" step="1" value={p.maps} onChange={e => patchPlayer(i, { maps: e.target.value })} /></td>
              <td><div className="future-team"><span className="future-team-name" aria-label={`队伍 ${i + 1}`} title="按已收录的选手资料匹配">{p.team || '暂未收录队伍'}</span><select aria-label={`队伍成绩 ${i + 1}`} disabled={!p.team} value={p.team_place} onChange={e => patchPlayer(i, { team_place: e.target.value })}>{['未设定', '冠军', '亚军', '四强', '八强', '小组淘汰'].map(x => <option key={x}>{x}</option>)}</select></div></td>
              <td><input aria-label={`EVP ${i + 1}`} type="checkbox" disabled={current.mvp_player === p.player_id} checked={current.mvp_player !== p.player_id && p.evp} onChange={e => patchPlayer(i, { evp: e.target.checked })} /></td>
              <td><button className="text-link" type="button" aria-label={`移除 ${playerById[p.player_id]?.name}`} disabled={current.players.length <= 1} onClick={() => patchEvent({ players: current.players.filter((_, j) => j !== i), mvp_player: current.mvp_player === p.player_id ? '' : current.mvp_player })}>移除</button></td>
            </tr>)}
          </tbody></table></div>
          <div className="future-mvp"><div><h3>03 / 设定本站 MVP</h3><p>每站最多一位；MVP 不自动意味着所在队伍夺冠。</p></div><label className="field">假设 MVP 得主<select aria-label="假设 MVP 得主" value={current.mvp_player} onChange={e => patchEvent({ mvp_player: e.target.value })}><option value="">暂不设定，仅模拟发挥</option>{current.players.map(p => <option key={p.player_id} value={p.player_id}>{playerById[p.player_id]?.name}</option>)}</select></label></div>
          <div className="future-submit"><span>{events.length} 站未来赛事 · 所有表现均为假设</span><button className="btn primary" disabled={busy}>{busy ? '正在计算…' : '推演这条 If 线'}</button></div>
        </form>}
        {result && <section className="future-result" aria-live="polite"><span className="future-kicker">SCENARIO RESULT / 02</span><h2>如果这些假设成立</h2>
          <p>已收录基线 → 加入 {result.assumption_manifest.length} 站后的条件排名。综合分为本站模型分，不是 HLTV 官方分数。</p>
          <div className="future-outcomes">{result.assumption_manifest.map(e => <div key={e.name}><small>{e.name}</small><b>{e.mvp_name === '未设定' ? 'MVP 未设定' : `${e.mvp_name} · 假设 MVP`}</b><span>{e.players.length} 位选手 · {e.start_date}</span></div>)}</div>
          <Table headers={['推演排名', '基线排名', '升降', '选手', '收录赛事 Rating', '图数', 'MVP', '综合分', '分数变化']} rows={result.rows.map(r => [r.rank, r.before_rank, r.change === 0 ? '—' : r.change > 0 ? `↑${r.change}` : `↓${-r.change}`, r.name, `${f(r.before_rating, 3)} → ${f(r.after_rating, 3)}`, `${r.before_maps} → ${r.after_maps}`, `${r.before_mvp} → ${r.after_mvp}`, `${f(r.before)} → ${f(r.after)}`, delta(r.score_delta)])} />
          <p className="future-caption">基线仅含已收录且已结束赛事，最晚结束日 {result.baseline_last_event_end}；快照更新 {result.baseline_snapshot_updated || '未注明'}。未设置的选手分数不变，名次可能因他人变化而移动。{result.excluded_records > 0 && `另有 ${result.excluded_records} 条缺日期或未结束记录未纳入。`}</p>
          <div className="actions"><Save title={`未来 If 线 · ${events.length} 站（${year}）`} payload={{ type: 'scenario', mode: 'future_events', year, events, result }} /><button className="btn" onClick={() => exportFile('未来If线推演.json', result)}>导出推演</button></div>
        </section>}
        <details className="future-method"><summary>推演依据与参考项目</summary><p>赛程核对日期：{catalog.verified_at}。已开赛赛事会自动退出可选列表，赛程不会自动联网更新。赛事级别及权重是本站评价设定。</p><p>Rating 按图数加权；表现、荣誉及队伍成绩按既有年度模型计算。这里回答“如果成立会怎样”，不提供获胜概率，不补造未来 ADR 或强敌数据。</p><p>参考 <a href="https://github.com/bootsh-zvuat/IFTV-TOP20" target="_blank" rel="noreferrer">IFTV-TOP20</a> 的逐赛事评分和排名对比思路；本页仅追加未来假设，历史记录保持固定。</p></details>
      </section>}
  </>;
}
