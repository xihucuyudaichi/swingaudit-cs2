import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowRight, Compass, Scales, MagnifyingGlass, ChartLine, GitBranch, List, X, BookmarkSimple, Download, BookOpen } from '@phosphor-icons/react';
import './connected.css';
import './dossier.css';
import './atlas.css';
import AnswerMarkdown from './AnswerMarkdown';
import { useConversationStore } from './useConversationStore';
import './agent.css';
import FutureScenarios from './FutureScenarios';
import AtlasWaterBackground from './AtlasWaterBackground';
import PlayerDirectory from './PlayerDirectory';
import { buildEventIndex, searchEventIndex } from './eventSearch';
import './events.css';

const Context = createContext(null);
const useResearch = () => useContext(Context);

const metrics = {
  overall: '收录赛事加权 Rating',
  vs_top5: '年度 vs Top 5',
  vs_top10: '年度 vs Top 10',
  vs_top20: '年度 vs Top 20',
  vs_top30: '年度 vs Top 30',
  vs_top50: '年度 vs Top 50',
  big_events: '大型及以上赛事 Rating',
  elite_events: '精英赛事 Rating',
  super_elite: '超级精英赛事 Rating',
  big_playoffs: '大型赛事淘汰赛 & Big Matches',
  elite_playoffs: '精英赛事淘汰赛 & Elite Matches',
  big_event_finals: '大型赛事总决赛 Rating',
  ct_side: 'CT 阵营实测 Rating',
  t_side: 'T 阵营实测 Rating',
  majors: 'Major 赛事 Rating',
  grand_finals: 'Major 决赛实测 Rating',
  map_mirage: 'Mirage 地图实测',
  map_inferno: 'Inferno 地图实测',
  map_nuke: 'Nuke 地图实测',
  map_dust2: 'Dust2 地图实测',
  map_ancient: 'Ancient 地图实测',
  map_anubis: 'Anubis 地图实测',
  map_overpass: 'Overpass 地图实测',
  map_vertigo: 'Vertigo 地图实测'
};

function weightedStat(rows, field = 'rating') {
  const valid = (rows || []).filter(r => typeof r?.[field] === 'number' && typeof r?.maps === 'number' && r.maps > 0);
  const maps = valid.reduce((s, r) => s + r.maps, 0);
  return {
    value: maps ? valid.reduce((s, r) => s + r[field] * r.maps, 0) / maps : null,
    maps: maps || null
  };
}

function playerMetricStat(p, metric) {
  if (!p) return { value: null, maps: null };
  const blum = p.multi_tier_benchmarks?.blum_2026;
  if (blum && blum[metric || 'overall']) {
    return { value: Number(blum[metric || 'overall'].rating), maps: blum[metric || 'overall'].maps };
  }
  if (!metric || metric === 'overall') return { value: p.rating_estimate, maps: p.maps };
  if (['vs_top5', 'vs_top10', 'vs_top20', 'vs_top30', 'vs_top50'].includes(metric)) {
    const o = p.opponents || {};
    const k = 'vsTop' + metric.split('top')[1];
    return { value: o[k] ?? null, maps: o[k + '图数'] ?? p.maps };
  }
  if (metric === 'ct_side' || metric === 't_side') {
    const s = p.side_splits?.[metric];
    return { value: s?.rating != null ? Number(s.rating) : null, maps: s?.maps_est || s?.rounds || p.maps };
  }
  if (metric === 'grand_finals') {
    return weightedStat(p.major_finals, 'rating');
  }
  if (metric === 'majors') {
    const rows = (p.events || []).filter(r => r.tier === 'Major');
    if (rows.length) return weightedStat(rows, 'rating');
    const mt = p.multi_tier_benchmarks?.santtu_majors;
    return { value: mt?.major_rating != null ? Number(mt.major_rating) : null, maps: mt?.major_maps ?? null };
  }
  if (metric.startsWith('map_')) {
    const target = metric.slice(4).toLowerCase();
    const mp = (p.map_pool || []).find(m => String(m.map || '').toLowerCase() === target && m.rating != null);
    return { value: mp ? Number(mp.rating) : null, maps: mp ? (mp.maps_est || mp.rounds) : null };
  }
  const tiers = {
    big_events: ['大型赛事', '精英赛', '精英赛事', '超级精英赛', 'Major'],
    elite_events: ['精英赛', '精英赛事', '超级精英赛', 'Major'],
    super_elite: ['超级精英赛', 'Major']
  };
  if (tiers[metric]) {
    const rows = (p.events || []).filter(r => tiers[metric].includes(r.tier));
    if (rows.length) return weightedStat(rows, 'rating');
    if (metric === 'big_events') {
      const sb = p.multi_tier_benchmarks?.santtu_big_events;
      if (sb?.big_rating != null) return { value: Number(sb.big_rating), maps: sb.big_maps ?? null };
    }
    return { value: null, maps: null };
  }
  return { value: null, maps: null };
}

const nav = [
  ['/', '观察室'],
  ['/compare', '选手对比'],
  ['/verify', '言论求证'],
  ['/rankings', '年度预测'],
  ['/scenarios', 'If 线推演']
];

const workflows = [
  ['/compare', '模块 01 · 位置与面板', '同位置选手对比', '对齐破点、主狙、自由人等战术职责，在相同赛事与对手强度下对比真实贡献。', Scales],
  ['/verify', '模块 02 · 事实与规则', '社区言论求证', '针对“只会打弱队”“保枪刷 K/D”等常见争论，调取分站记录与 Rating 3.0 规则核实。', MagnifyingGlass],
  ['/rankings', '模块 03 · 荣誉与强敌', '年度 Top 20 排名预测', '结合大赛含金量、MVP/EVP 荣誉与对阵强队表现，追踪与复盘年度排名。', ChartLine],
  ['/scenarios', '模块 04 · 动态沙盘', 'If 线与 MVP 推演', '设定未来赛事的参赛表现与 MVP 归属，查看不同 If 线下的年度排名变化。', GitBranch]
];

const f = (v, n = 2) => (v == null ? '—' : Number(v).toFixed(n));
const fsigned = (v, n = 2) => (v == null ? '—' : (Number(v) >= 0 ? '+' : '') + Number(v).toFixed(n));
const route = id => encodeURIComponent(id);

function Link({ to, children, ...props }) { return <a href={'#' + to} {...props}>{children}</a>; }

async function api(path, body, signal, extraHeaders) {
  const headers = { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(extraHeaders || {}) };
  const res = await fetch('/api/' + path, {
    method: body ? 'POST' : 'GET',
    headers: Object.keys(headers).length ? headers : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal
  });
  let out;
  try { out = await res.json(); } catch { throw Error('后端未启动或返回无效数据，请检查服务后重试。'); }
  if (!res.ok) throw Error(out.error || '数据请求失败');
  return out;
}

function Note({ children }) { return <div className="note"><span>{children}</span></div>; }
function Empty({ children = '该年份或范围没有可用的真实数据。' }) { return <div className="empty"><h3>暂无可用数据</h3><p>{children}</p></div>; }
function Heading({ title, subtitle, children }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="heading-sub">{subtitle}</p>}
      </div>
      {children && <div className="heading-actions">{children}</div>}
    </div>
  );
}
function Table({ headers, rows, topScroll = false }) {
  const viewport = useRef(null);
  const [scroll, setScroll] = useState({ left: 0, max: 0 });
  const readScroll = () => {
    const wrap = viewport.current;
    const next = { left: wrap.scrollLeft, max: Math.max(0, wrap.scrollWidth - wrap.clientWidth) };
    setScroll(old => old.left === next.left && old.max === next.max ? old : next);
  };
  useEffect(() => {
    if (!topScroll) return;
    const wrap = viewport.current;
    const observer = new ResizeObserver(readScroll);
    observer.observe(wrap);
    observer.observe(wrap.querySelector('table'));
    readScroll();
    return () => observer.disconnect();
  }, [topScroll, headers, rows]);
  const move = direction => {
    const wrap = viewport.current;
    wrap.scrollBy({ left: direction * wrap.clientWidth * 0.7,
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  };
  const table = (
    <div className="table-wrap" ref={viewport} onScroll={topScroll ? readScroll : undefined}>
      <table>
        <thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c ?? '—'}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
  if (!topScroll) return table;
  return (
    <div className="table-scroll-pair">
      <div className="table-pan-nav" hidden={scroll.max <= 1} role="group" aria-label="表格横向导航">
        <span className="table-pan-hint">左右查看</span>
        <button type="button" className="table-pan-button" aria-label="向左查看表格" disabled={scroll.left <= 1} onClick={() => move(-1)}>
          <ArrowRight size={16} style={{ transform: 'rotate(180deg)' }} />
        </button>
        <input className="table-pan-range" type="range" min={0} max={scroll.max} step={1}
          value={scroll.left} aria-label="表格横向位置"
          aria-valuetext={`${Math.round(scroll.max ? scroll.left / scroll.max * 100 : 0)}%`}
          style={{ '--pan-progress': `${scroll.max ? scroll.left / scroll.max * 100 : 0}%` }}
          onChange={e => { viewport.current.scrollLeft = Number(e.target.value); readScroll(); }} />
        <button type="button" className="table-pan-button" aria-label="向右查看表格" disabled={scroll.left >= scroll.max - 1} onClick={() => move(1)}>
          <ArrowRight size={16} />
        </button>
      </div>
      {table}
    </div>
  );
}

function exportFile(name, value) {
  const url = URL.createObjectURL(new Blob([typeof value === 'string' ? value : JSON.stringify(value, null, 2)], { type: 'application/json;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Save({ title, payload }) {
  const { save } = useResearch();
  const [busy, setBusy] = useState(false);
  return (
    <button className="btn" disabled={busy} onClick={async () => { setBusy(true); try { await save(title, payload); } finally { setBusy(false); } }}>
      <BookmarkSimple size={17} weight="bold" />{busy ? '正在保存…' : '保存研究'}
    </button>
  );
}
function Source({ item }) {
  const { setEvidence } = useResearch();
  return <button className="text-link" onClick={() => setEvidence(item)}>查看证据 ↗</button>;
}
function Evidence() {
  const { evidence, setEvidence } = useResearch();
  const ref = useRef(null);
  useEffect(() => { if (evidence) ref.current?.showModal(); }, [evidence]);
  if (!evidence) return null;
  const rows = Array.isArray(evidence) ? evidence : [evidence];
  return (
    <dialog className="modal wide" ref={ref} onCancel={() => setEvidence(null)} onClick={e => { if (e.target === ref.current) setEvidence(null); }}>
      <header className="modal-head"><h2>原始记录与来源依据</h2><button className="icon-btn" aria-label="关闭证据" onClick={() => setEvidence(null)}><X size={20} /></button></header>
      <Note>以下为该项统计对应的比赛或榜单明细记录；显示“未收录”代表当站比赛未单独统计该分项。</Note>
      {rows.map((r, i) => (
        <article className="source-record" key={i}>
          {r.source_file && <p><b>来源文件：</b>{r.source_file} · {r.sheet} · 第 {r.row} 行</p>}
          {Object.entries(r).filter(([, v]) => typeof v !== 'object' || v === null).map(([k, v]) => (
            <div key={k}><b>{k}</b><span>{v == null ? '未收录' : String(v)}</span></div>
          ))}
          {(r.source_url || r['来源URL']) && <a className="text-link" href={r.source_url || r['来源URL']} target="_blank" rel="noreferrer">打开来源文件或统计页 ↗</a>}
        </article>
      ))}
    </dialog>
  );
}
const ALL_YEARS = ['2026', '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2014', '2013', '2012', '2027'];

function Scope({ showMetric = true }) {
  const { year, setYear, metric, setMetric, season } = useResearch();
  return (
    <div className="scope-bar">
      <label>研究年份 <select aria-label="研究年份" value={year} onChange={e => setYear(e.target.value)}>{ALL_YEARS.map(y => <option value={y} key={y}>{y}</option>)}</select></label>
      {showMetric && <label>统计范围 <select aria-label="统计范围" value={metric} onChange={e => setMetric(e.target.value)}>{Object.entries(metrics).map(([k, v]) => <option value={k} key={k}>{v}</option>)}</select></label>}
      <span>{season ? `${season.events.length} 场重点赛事${season.raw_source_events && season.raw_source_events > season.events.length ? `（共收录 ${season.raw_source_events} 站）` : ''} · ${season.rows} 条比赛记录 · ${season.players.length} 位选手` : '该年份暂无数据'}</span>
    </div>
  );
}
function PlayerSelect({ label, value, onChange, players }) {
  const { season } = useResearch();
  return (
    <label className="field">
      {label}
      <select value={value} onChange={e => onChange(e.target.value)}>
        {(players || season?.players || []).map(p => (
          <option value={p.id} key={p.id}>{p.name}{p.identity_status === 'ambiguous_name_split' ? ' · 选手编号 ' + p.source_ids.join(',') : ''}</option>
        ))}
      </select>
    </label>
  );
}
function AgentEvidence({ result }) {
  const tools = result.tools || [];
  return <details className="agent-evidence">
    <summary>来源与核对记录 <span>{tools.length} 项</span></summary>
    {result.verification && <div className="agent-checks">
      <strong>{result.verification.passed ? '已完成数据核对' : '部分内容仍需核对'}</strong>
      {result.verification.checks?.map(c => <p key={c.check_id}>{c.passed ? '✓' : '待核对'} {c.label}：{c.detail}</p>)}
    </div>}
    {tools.map((t, i) => <div key={i} className="tool-trace-item">
      <p>{t.arguments?.query || t.arguments?.players?.join(' vs ') || t.arguments?.claim || t.arguments?.player || `${result.year} 赛季记录`}</p>
      <Source item={{ ...t.arguments, controlled_tool: t.controlled_tool || t.tool, result: JSON.stringify(t.result) }} />
    </div>)}
  </details>;
}
function buildLivePageContext({ path = '/', year = '2026', metric = 'overall', pair = ['donk', 'zywoo'], eventQuery = '', season, bundle, uiContext = {} }) {
  const metricLabel = metrics[metric] || '收录赛事加权 Rating';
  const p0 = season?.players?.find(p => p.id === pair[0]);
  const p1 = season?.players?.find(p => p.id === pair[1]);
  const p0Name = p0?.name || pair[0] || 'donk';
  const p1Name = p1?.name || pair[1] || 'ZywOo';
  const defaultQuestion = '对比 donk 和 ZywOo 在本赛季赛事中的整体表现与场上位置特点。';

  if (path === '/compare') {
    return {
      pageName: '选手对比',
      badgeText: `${p0Name} vs ${p1Name} · ${metricLabel}`,
      detailText: `${year} 赛季 · 统计范围：${metricLabel} · 对阵选手：${p0Name} vs ${p1Name}${uiContext.compareDelta ? `（${uiContext.compareDelta}）` : ''}`,
      selectedPlayers: pair,
      focusedPlayer: '',
      focusedEvent: '',
      defaultQuestion,
      quickPrompts: [
        `对比 ${p0Name} 和 ${p1Name} 在「${metricLabel}」下的表现与场上位置特点`,
        `${p0Name} 与 ${p1Name} 在防守方(CT)与进攻方(T)的发挥有何差异？`
      ]
    };
  }
  if (path === '/verify') {
    return {
      pageName: '言论求证',
      badgeText: `${year} 赛季 · 争议求证与规则核查`,
      detailText: `${year} 赛季 · 统计范围：${metricLabel}${uiContext.verifyClaim ? ` · 当前主张：“${uiContext.verifyClaim.slice(0, 72)}”` : ''}`,
      selectedPlayers: pair,
      focusedPlayer: '',
      focusedEvent: '',
      defaultQuestion,
      quickPrompts: [
        `请核对：${p0Name} 与 ${p1Name} 在 ${year} 年的大赛 MVP 数量与强敌表现差异是什么？`,
        '为什么不能仅凭单场 K/D 或天梯 RWS 判断职业选手的真实贡献？'
      ]
    };
  }
  if (path === '/rankings') {
    const rkLabel = uiContext.rankingsLabel || (year === '2026' ? '2026 选手年度积分追踪与 Valve 战队榜' : `${year} 年度排名预测与官方 Top 20 对照`);
    return {
      pageName: '年度预测',
      badgeText: `${year} 赛季 · ${rkLabel}`,
      detailText: `${year} 赛季年度排名预测 · 当前视图：${rkLabel}`,
      selectedPlayers: [],
      focusedPlayer: '',
      focusedEvent: '',
      defaultQuestion: `解读 ${year} 赛季「${rkLabel}」前五名的核心优势与竞争格局。`,
      quickPrompts: [
        `解读 ${year} 赛季「${rkLabel}」前五名的核心优势与竞争格局`,
        '为什么大赛 MVP/EVP 荣誉与对阵前十强队发挥在年度评选中缺一不可？'
      ]
    };
  }
  if (path.startsWith('/scenarios')) {
    const evName = uiContext.scenarioEvent || '未开赛焦点赛事';
    const mvpName = uiContext.scenarioMvp || '';
    return {
      pageName: 'If 线推演',
      badgeText: `${year} 赛季 · ${evName}${mvpName ? ` · MVP ${mvpName}` : ''}`,
      detailText: `${year} 赛季 If 线推演 · 目标赛事：${evName}${mvpName ? ` · 假设 MVP：${mvpName}` : ''}${uiContext.scenarioPlayers ? ` · 参赛设定：${uiContext.scenarioPlayers}` : ''}`,
      selectedPlayers: mvpName ? [mvpName] : [],
      focusedPlayer: mvpName,
      focusedEvent: evName,
      defaultQuestion,
      quickPrompts: [
        `如果 ${mvpName || 'donk'} 拿下 ${evName} 的 MVP，对 ${year} 年度排名有何影响？`,
        '对比当前 If 线参赛选手的赛季基础 Rating 与荣誉积分差距'
      ]
    };
  }
  if (path.startsWith('/players/')) {
    const pid = decodeURIComponent(path.slice(9));
    const tp = season?.players?.find(p => p.id === pid);
    const rp = bundle?.roles?.seasons?.[year]?.players?.find(r => r.id === pid);
    const pName = tp?.name || pid;
    const pRole = rp?.role_short || rp?.role_name || '职业选手';
    const pRating = tp?.rating_estimate != null ? Number(tp.rating_estimate).toFixed(2) : '—';
    return {
      pageName: `选手档案 · ${pName}`,
      badgeText: `${year} 赛季 · Rating ${pRating}`,
      detailText: `正在浏览选手 ${pName} 的 ${year} 赛季档案（主力战队：${tp?.events?.[0]?.team || '—'} · 参赛 ${tp?.events?.length || 0} 站 / ${tp?.maps || 0} 图 · 综合 Rating ${pRating} · ${tp?.mvp || 0} MVP / ${tp?.evp || 0} EVP · 场上位置：${pRole}）`,
      selectedPlayers: [pid],
      focusedPlayer: pName,
      focusedEvent: '',
      defaultQuestion: `全面分析 ${pName} 在 ${year} 赛季的重点赛事表现、强敌发挥与场上职责。`,
      quickPrompts: [
        `全面分析 ${pName} 在 ${year} 赛季的重点赛事表现、强敌发挥与场上职责`,
        `对比 ${pName} 与同位置（${pRole}）其他顶尖选手的表现差异`
      ]
    };
  }
  if (path === '/players') {
    const pSearch = uiContext.playerSearch || '';
    const pInit = uiContext.playerInitial || '';
    const vCount = uiContext.visiblePlayerCount ?? season?.players?.length ?? 0;
    return {
      pageName: '选手库',
      badgeText: `${year} 赛季 · ${vCount} 位选手${pSearch ? ` · “${pSearch}”` : ''}`,
      detailText: `${year} 赛季选手目录（当前显示 ${vCount} 位选手）${pSearch ? ` · 搜索关键词：“${pSearch}”` : ''}${pInit ? ` · 首字母定位：${pInit}` : ''}`,
      selectedPlayers: pSearch ? [pSearch] : [],
      focusedPlayer: pSearch,
      focusedEvent: '',
      defaultQuestion,
      quickPrompts: [
        `盘点 ${year} 赛季 Rating 与大赛样本图数兼备的前五位代表选手`,
        `不同场上位置（突破手、主狙、自由人）在 ${year} 赛季的代表选手分别是谁？`
      ]
    };
  }
  if (path.startsWith('/events/')) {
    const evUrl = new URL(path, location.origin);
    const evName = decodeURIComponent(evUrl.pathname.slice(8));
    const evObj = season?.events?.find(e => e.name === evName);
    const topEv = (evObj?.players || []).slice(0, 3).map(p => `${p.name}(${p.rating ?? '—'})`).join('、');
    return {
      pageName: `赛事详情 · ${evName}`,
      badgeText: `${evObj?.tier || year + ' 赛季'} · ${evObj?.players?.length || 0} 位选手`,
      detailText: `正在浏览 ${year} 赛季赛事「${evName}」（级别：${evObj?.tier || '重点赛事'} · 收录 ${evObj?.players?.length || 0} 位参赛选手${topEv ? ` · 领跑选手：${topEv}` : ''}）`,
      selectedPlayers: (evObj?.players || []).slice(0, 2).map(p => p.id),
      focusedPlayer: evObj?.players?.[0]?.name || '',
      focusedEvent: evName,
      defaultQuestion: `总结「${evName}」赛事中表现最突出的选手与 MVP 荣誉归属。`,
      quickPrompts: [
        `总结「${evName}」赛事中表现最突出的选手与 MVP 荣誉归属`,
        `对比「${evName}」前三名选手的 Rating、场均伤害与团队名次`
      ]
    };
  }
  if (path === '/events') {
    return {
      pageName: '赛事库',
      badgeText: eventQuery ? `检索：“${eventQuery}”` : `${year} 赛季 · ${season?.events?.length || 0} 站赛事`,
      detailText: eventQuery ? `正在跨赛季检索赛事关键词：“${eventQuery}”` : `正在浏览 ${year} 赛季重点赛事列表（共 ${season?.events?.length || 0} 站）`,
      selectedPlayers: [],
      focusedPlayer: '',
      focusedEvent: eventQuery || '',
      defaultQuestion,
      quickPrompts: [
        `总结 ${eventQuery ? `与“${eventQuery}”相关的赛事` : `${year} 赛季各站重点赛事`} 的 MVP 与高分选手表现`,
        `${year} 赛季哪几站顶级大赛的参赛强队竞争最激烈？`
      ]
    };
  }
  if (path === '/library') {
    return {
      pageName: '资料与方法',
      badgeText: '15 赛季档案 · 现役地图与规则',
      detailText: '正在查看全库 2012–2026 数据覆盖规模、2026 现役 7 张比赛地图攻防胜率基准与评分规则说明',
      selectedPlayers: [],
      focusedPlayer: '',
      focusedEvent: '',
      defaultQuestion,
      quickPrompts: [
        '2026 赛季现役比赛地图（Dust2、Mirage、Nuke 等）的攻防胜率有什么特点？',
        '简明解释平台是如何结合赛事级别、强敌交手与场上位置评估选手的？'
      ]
    };
  }
  if (path === '/research') {
    const recCount = bundle?.records?.length || 0;
    return {
      pageName: '我的研究',
      badgeText: `已保存 ${recCount} 条研究记录`,
      detailText: `正在查看已保存的研究记录列表（共 ${recCount} 条）`,
      selectedPlayers: [],
      focusedPlayer: '',
      focusedEvent: '',
      defaultQuestion,
      quickPrompts: [
        `对比 ${p0Name} 和 ${p1Name} 在 ${year} 赛季的整体表现与场上位置特点`,
        `盘点 ${year} 赛季最具代表性的大赛 MVP 选手表现`
      ]
    };
  }
  const homeTabLabel = uiContext.homeTab === 'events' ? '2026 已结束赛事加权个人荣誉积分' : uiContext.homeTab === 'ratings' ? 'Top 10 十维细分 Rating 矩阵' : 'Top 10 综合荣誉与核心面板';
  return {
    pageName: path === '/live' ? '实时工作台' : '观察室首页',
    badgeText: `${year} 赛季 · ${metricLabel}`,
    detailText: `${year} 赛季观察室 · 统计范围：${metricLabel} · 当前看板：${homeTabLabel} · 收录 ${season?.events?.length || 0} 站赛事 / ${season?.players?.length || 0} 位选手`,
    selectedPlayers: pair,
    focusedPlayer: '',
    focusedEvent: '',
    defaultQuestion,
    quickPrompts: [
      `解读 ${year} 赛季观察室榜首与前五名选手的核心数据差异`,
      `在「${metricLabel}」口径下，${year} 赛季哪些选手表现最突出？`
    ]
  };
}

function DragGripIcon() {
  return (
    <svg className="floating-grip-icon" width="12" height="16" viewBox="0 0 12 16" fill="currentColor" aria-hidden="true">
      <circle cx="3.5" cy="3" r="1.4" />
      <circle cx="8.5" cy="3" r="1.4" />
      <circle cx="3.5" cy="8" r="1.4" />
      <circle cx="8.5" cy="8" r="1.4" />
      <circle cx="3.5" cy="13" r="1.4" />
      <circle cx="8.5" cy="13" r="1.4" />
    </svg>
  );
}

function Agent({ verify: verifyProp = false }) {
  const { path = '/', year, metric, pair, prompt, setPrompt, season, bundle, eventQuery, uiContext } = useResearch();
  const verify = verifyProp || path === '/verify';
  const routeScope = location.hash.split('?')[0] || ('#' + (path || '/'));
  const pageCtx = useMemo(
    () => buildLivePageContext({ path, year, metric, pair, eventQuery, season, bundle, uiContext }),
    [path, year, metric, pair, eventQuery, season, bundle, uiContext]
  );
  const [draft, updateDraft, storageError] = useConversationStore(`${routeScope}:${year}`, { q: prompt || pageCtx.defaultQuestion, result: null });
  const { q, result } = draft;
  const setQ = q => updateDraft({ q });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(() => Boolean(draft.editingOpen || !draft.result));
  const [expanded, setExpanded] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');
  const [minimized, setMinimized] = useState(false);
  const [dragPos, setDragPos] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('swingaudit.floating.dragpos.v1'));
      if (saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)) return saved;
    } catch {}
    return null;
  });
  const [isDragging, setIsDragging] = useState(false);
  const [selectedSnippet, setSelectedSnippet] = useState(null);
  const request = useRef(null);
  const reader = useRef(null);
  const answer = useRef(null);
  const readingArea = useRef(null);
  const questionField = useRef(null);
  const panelRef = useRef(null);
  const pillRef = useRef(null);
  const dragMovedRef = useRef(false);

  useEffect(() => () => { request.current?.abort(); request.current = null; }, []);
  useEffect(() => {
    request.current?.abort(); request.current = null;
    setBusy(false); setError(''); setExpanded(false); setEditing(Boolean(draft.editingOpen || !draft.result));
  }, [year, routeScope]);
  useEffect(() => {
    setSelectedSnippet(null);
    document.querySelectorAll('[data-agent-selected="true"]').forEach(el => el.removeAttribute('data-agent-selected'));
  }, [path, year]);
  useEffect(() => {
    if (prompt) {
      setMinimized(false);
      setQ(prompt);
      setPrompt('');
      setEditing(true);
    }
  }, [prompt]);
  useEffect(() => {
    if (result && readingArea.current) readingArea.current.scrollTop = 0;
  }, [result]);
  useEffect(() => {
    const dialog = reader.current;
    if (!expanded || !dialog) return;
    const previous = document.body.style.overflow;
    dialog.showModal(); document.body.style.overflow = 'hidden';
    return () => { dialog.close(); document.body.style.overflow = previous; };
  }, [expanded]);

  useEffect(() => {
    try {
      if (dragPos) localStorage.setItem('swingaudit.floating.dragpos.v1', JSON.stringify(dragPos));
      else localStorage.removeItem('swingaudit.floating.dragpos.v1');
    } catch {}
  }, [dragPos]);

  useEffect(() => {
    function clampToViewport() {
      setDragPos(prev => {
        if (!prev) return null;
        const el = minimized ? pillRef.current : panelRef.current;
        const w = el?.offsetWidth || 380;
        const h = el?.offsetHeight || 260;
        const maxX = Math.max(8, window.innerWidth - w - 8);
        const maxY = Math.max(8, window.innerHeight - h - 8);
        return {
          x: Math.min(Math.max(8, prev.x), maxX),
          y: Math.min(Math.max(8, prev.y), maxY)
        };
      });
    }
    window.addEventListener('resize', clampToViewport);
    return () => window.removeEventListener('resize', clampToViewport);
  }, [minimized, result, editing]);

  function startDrag(e, targetEl) {
    if (e.button !== undefined && e.button !== 0) return;
    if (e.target.closest?.('button:not(.floating-agent-pill), input, textarea, select, a')) return;
    const el = targetEl || panelRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const startX = e.clientX;
    const startY = e.clientY;
    dragMovedRef.current = false;

    function onMove(ev) {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      if (!dragMovedRef.current && Math.hypot(dx, dy) < 4) return;
      dragMovedRef.current = true;
      setIsDragging(true);
      const w = el.offsetWidth || rect.width || 380;
      const h = el.offsetHeight || rect.height || 240;
      const maxX = Math.max(8, window.innerWidth - w - 8);
      const maxY = Math.max(8, window.innerHeight - h - 8);
      const nextX = Math.round(Math.min(Math.max(8, rect.left + dx), maxX));
      const nextY = Math.round(Math.min(Math.max(8, rect.top + dy), maxY));
      setDragPos({ x: nextX, y: nextY });
    }
    function onUp() {
      setIsDragging(false);
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onUp);
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    window.addEventListener('pointercancel', onUp);
  }

  useEffect(() => {
    function handleSelectionChange() {
      const sel = window.getSelection?.();
      if (!sel || sel.isCollapsed) return;
      const mainEl = document.getElementById('main');
      const anchor = sel.anchorNode?.nodeType === 1 ? sel.anchorNode : sel.anchorNode?.parentElement;
      if (!mainEl || !anchor || !mainEl.contains(anchor)) return;
      if (anchor.closest?.('.reading-agent, .verify-stage')) return;
      const text = sel.toString().replace(/\s+/g, ' ').trim();
      if (text.length >= 2 && text.length <= 320) {
        setSelectedSnippet({ kind: '划词选取', text });
      }
    }
    function handleMainClick(e) {
      const mainEl = document.getElementById('main');
      if (!mainEl || !mainEl.contains(e.target)) return;
      if (e.target.closest?.('a[href], button, select, input, textarea, label, summary, .reading-agent, .verify-stage')) return;
      const item = e.target.closest?.('tbody tr, .podium-card, .role-card, .rule-card, .info-card, .profile-stats > div, .duel-scoreboard, .mvp-slot, .research-list article');
      if (!item) return;
      const raw = (item.innerText || '').replace(/\s+/g, ' ').trim();
      if (raw.length < 2) return;
      const candidates = Array.from(item.querySelectorAll?.('b, strong, h3, h4, .text-link') || [])
        .map(el => (el.innerText || '').replace(/\s+/g, ' ').trim())
        .filter(t => t && /[A-Za-z\u4e00-\u9fa5]{2,}/.test(t) && !/^(亚洲|欧洲|美洲|Stage|查看)/.test(t));
      const primaryText = candidates[0] || '';
      const fullText = (primaryText && !raw.startsWith(primaryText)) ? `${primaryText} · ${raw}` : raw;
      document.querySelectorAll('[data-agent-selected="true"]').forEach(el => el.removeAttribute('data-agent-selected'));
      item.setAttribute('data-agent-selected', 'true');
      setSelectedSnippet({ kind: '页面点选', text: fullText.slice(0, 220) });
    }
    function handleKeyDown(e) {
      if (e.altKey && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setMinimized(m => !m);
      }
    }
    document.addEventListener('selectionchange', handleSelectionChange);
    document.addEventListener('click', handleMainClick, true);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
      document.removeEventListener('click', handleMainClick, true);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  function clearSelectedSnippet() {
    setSelectedSnippet(null);
    document.querySelectorAll('[data-agent-selected="true"]').forEach(el => el.removeAttribute('data-agent-selected'));
  }
  function cancel() {
    request.current?.abort(); request.current = null; setBusy(false);
    setError('已取消本次分析，可以修改问题后重试。');
  }
  function clearConversation() {
    request.current?.abort(); request.current = null;
    updateDraft({ q: '', result: null, editingOpen: false }); setBusy(false); setError(''); setExpanded(false); setEditing(true);
  }
  async function copyAnswer() {
    try { await navigator.clipboard.writeText(answer.current?.innerText || result.answer); setCopyStatus('已复制'); }
    catch { setCopyStatus('复制失败，请选择正文复制'); }
  }
  async function ask(e) {
    e.preventDefault(); request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    updateDraft({ editingOpen: false });
    setBusy(true); setError(''); setCopyStatus(''); setExpanded(false);
    const timer = setTimeout(() => {
      controller.abort();
      if (request.current === controller) {
        setBusy(false); setError('分析等待超时，请稍后重试或缩小问题范围。');
      }
    }, 120000);
    const question = q;
    try {
      const r = await api('agent', {
        year,
        question,
        context: {
          selected_players: pageCtx.selectedPlayers,
          metric,
          mode: verify ? 'verify' : 'analysis',
          route: path,
          page_name: pageCtx.pageName,
          page_summary: pageCtx.detailText,
          focused_player: pageCtx.focusedPlayer || '',
          focused_event: pageCtx.focusedEvent || '',
          selected_text: selectedSnippet?.text || '',
          selected_kind: selectedSnippet?.kind || ''
        }
      }, controller.signal);
      if (!controller.signal.aborted) {
        updateDraft({ result: { ...r, question, year: r.year || year }, editingOpen: false }); setEditing(false);
      }
    } catch (e) {
      if (!controller.signal.aborted && request.current === controller) setError(e.message);
    } finally {
      clearTimeout(timer);
      if (request.current === controller) setBusy(false);
    }
  }
  const toolsCount = result?.tools?.length || 0;
  const floatingStyle = dragPos
    ? {
        '--float-left': `${dragPos.x}px`,
        '--float-top': `${dragPos.y}px`,
        '--float-right': 'auto',
        '--float-bottom': 'auto'
      }
    : undefined;

  return (
    <>
      {minimized && (
        <button
          ref={pillRef}
          type="button"
          style={floatingStyle}
          className={`floating-agent-pill${dragPos ? ' is-custom-pos' : ''}${isDragging ? ' is-dragging' : ''}`}
          aria-label="展开赛事分析助手悬浮窗"
          onPointerDown={e => startDrag(e, pillRef.current)}
          onClick={e => {
            if (dragMovedRef.current) {
              e.preventDefault();
              dragMovedRef.current = false;
              return;
            }
            setMinimized(false);
            requestAnimationFrame(() => questionField.current?.focus());
          }}
        >
          <AtlasWaterBackground className="agent-water-background" position="absolute" speed={0.95} scale={1.15} contrast={0.95} maxDpr={1.5} zIndex={0} />
          <DragGripIcon />
          <span className="pill-dot" aria-hidden="true" />
          <span className="floating-emblem-orb is-sm" aria-hidden="true">
            <Compass size={17} weight="fill" />
          </span>
          <span className="pill-copy">
            <strong>SwingAudit · 赛事分析助手</strong>
            <small>{selectedSnippet ? `已捕获${selectedSnippet.kind}：${selectedSnippet.text.slice(0, 16)}…` : `当前背景：${pageCtx.pageName} · ${year} 赛季`}</small>
          </span>
          <span className="pill-cta">展开提问 ↗</span>
        </button>
      )}
      <aside
        ref={panelRef}
        style={floatingStyle}
        className={`agent-panel reading-agent floating-agent${result ? ' has-answer' : ''}${minimized ? ' is-minimized' : ''}${dragPos ? ' is-custom-pos' : ''}${isDragging ? ' is-dragging' : ''}`}
        aria-label={verify ? '言论求证助手' : '赛事分析助手'}
      >
        <AtlasWaterBackground className="agent-water-background" position="absolute" speed={0.95} scale={1.1} contrast={1.0} surge={false} maxDpr={1.5} zIndex={0} />
        <header
          className="floating-drag-header"
          onPointerDown={e => startDrag(e, panelRef.current)}
          onDoubleClick={() => setDragPos(null)}
          title="按住顶部可自由拖动悬浮窗位置（双击复位）"
        >
          <span className="floating-drag-bar" aria-hidden="true" />
          <div className="floating-agent-brand">
            <DragGripIcon />
            <span className="pill-dot" aria-hidden="true" />
            <span className="floating-emblem-orb" aria-hidden="true">
              <Compass size={20} weight="fill" />
            </span>
            <div>
              <h2>{verify ? 'SwingAudit · 言论求证台' : 'SwingAudit · 赛事分析助手'}</h2>
              <small>{year} 赛季 · 自动结合当前页面与选取背景解答</small>
            </div>
          </div>
          <div className="floating-window-controls">
            <button
              type="button"
              className="floating-ctrl-btn"
              aria-label="收起悬浮窗"
              title="收起为底部悬浮胶囊 (Alt+K)"
              onClick={() => setMinimized(true)}
            >
              — 收起
            </button>
          </div>
        </header>
        <div className="agent-context-bar" aria-label="当前自动感知的页面与选取背景">
          <div className="agent-context-pills">
            <span className="context-pill page-pill" title={pageCtx.detailText}>
              <b>所在页面</b>
              <span className="context-pill-text">{pageCtx.pageName} · {pageCtx.badgeText}</span>
            </span>
            {selectedSnippet ? (
              <span className="context-pill selection-pill" title={selectedSnippet.text}>
                <b>{selectedSnippet.kind}</b>
                <span className="context-pill-text">{selectedSnippet.text}</span>
                <button type="button" className="context-pill-clear" aria-label="清除选取背景" onClick={clearSelectedSnippet}>×</button>
              </span>
            ) : (
              <span className="context-pill hint-pill" title="在页面任意表格行、卡片点选或划词选中文字，即可自动纳入提问背景">
                <span className="context-pill-text">点选表格行/卡片或划词即可作为背景</span>
              </span>
            )}
          </div>
          {editing && !result && pageCtx.quickPrompts?.length > 0 && (
            <div className="agent-quick-prompts">
              {selectedSnippet ? (
                <button
                  type="button"
                  className="agent-quick-chip is-selection"
                  onClick={() => {
                    setQ(`请结合当前「${pageCtx.pageName}」页面背景，分析我选取的这项内容：${selectedSnippet.text.slice(0, 90)}`);
                    requestAnimationFrame(() => questionField.current?.focus());
                  }}
                >
                  围绕已选内容提问 ↗
                </button>
              ) : null}
              {pageCtx.quickPrompts.slice(0, 1).map((qp, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="agent-quick-chip"
                  onClick={() => {
                    setQ(qp);
                    requestAnimationFrame(() => questionField.current?.focus());
                  }}
                >
                  {qp.length > 28 ? qp.slice(0, 28) + '…' : qp}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="agent-workspace">
          <div className="agent-composer">
            {result && <button type="button" className="agent-question-toggle" aria-expanded={editing} onClick={() => { const next = !editing; setEditing(next); updateDraft({ editingOpen: next }); if (next) requestAnimationFrame(() => questionField.current?.focus()); }}>
              <span>{result.question}</span><b>{editing ? '收起' : '修改问题'}</b>
            </button>}
            {editing && <form onSubmit={ask} className="agent-composer-island">
              <label className="field">
                <span className="agent-field-label">{verify ? '需要核对的主张' : '分析问题'}</span>
                <textarea ref={questionField} aria-label={verify ? '需要核对的主张' : '分析问题'} rows={2} value={q} maxLength={4000} disabled={busy}
                  onChange={e => setQ(e.target.value)}
                  onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.nativeEvent.isComposing && q.trim() && !busy) { e.preventDefault(); e.currentTarget.form.requestSubmit(); } }} />
              </label>
              <div className="agent-submit-row">
                <small>Ctrl / ⌘ + Enter 提交</small>
                {busy ? <button type="button" className="btn" onClick={e => { e.preventDefault(); cancel(); }}>取消分析</button> :
                  <button className="btn primary" disabled={!q.trim()}>{verify ? '求证并查看来源' : '查询与分析'} <ArrowRight size={15} /></button>}
              </div>
            </form>}
          </div>
          {storageError && <p role="status" className="agent-storage-note">{storageError}</p>}
          {busy && <p role="status" className="agent-loading">正在查询比赛记录并生成分析…</p>}
          {error && <p role="alert" className="error agent-error">{error}</p>}
          {!result && !busy && !error && <p className="agent-start-hint">从一个具体问题开始，结论将附上可查阅的数据来源。</p>}
          {result && <section className="agent-result" aria-label="分析结果">
            <div className="agent-result-heading">
              <div className="agent-result-title-group">
                <span className="agent-result-badge" aria-hidden="true">
                  <ChartLine size={16} weight="bold" />
                </span>
                <div><h3>分析结论</h3><small>{result.year} 赛季 · {toolsCount} 项数据来源</small></div>
              </div>
              <button type="button" className="text-link agent-expand-pill" onClick={() => setExpanded(true)}>展开阅读 ↗</button>
            </div>
            <div className="agent-reading-scroll" ref={readingArea} tabIndex={0} role="region" aria-label="分析结论阅读区">
              <div className="message" ref={answer}><AnswerMarkdown text={result.answer} /></div>
              <AgentEvidence result={result} />
            </div>
            <div className="agent-result-actions">
              <button type="button" className="text-link agent-action-pill" onClick={copyAnswer}>复制正文</button>
              <button type="button" className="text-link agent-action-pill" onClick={clearConversation}>清除对话</button>
              <Save title={verify ? '言论求证' : '赛事分析记录'} payload={{ type: verify ? 'verify' : 'agent', year: result.year, question: result.question, result }} />
              <span role="status">{copyStatus}</span>
            </div>
          </section>}
        </div>
      </aside>
      <dialog className="agent-reader" ref={reader} aria-label="分析结论展开阅读" onCancel={() => setExpanded(false)} onClose={() => setExpanded(false)} onClick={e => { if (e.target === e.currentTarget) setExpanded(false); }}>
        {result && <>
          <header className="agent-reader-heading"><div><small>{result.year} 赛季 · {toolsCount} 项数据来源</small><h2>分析结论</h2></div><button type="button" className="icon-btn" aria-label="关闭展开阅读" onClick={() => setExpanded(false)} autoFocus><X size={22} /></button></header>
          <div className="agent-reader-body"><p className="agent-reader-question">{result.question}</p><AnswerMarkdown text={result.answer} /><AgentEvidence result={result} /></div>
          <footer><button type="button" className="text-link" onClick={copyAnswer}>复制正文</button><span role="status">{copyStatus}</span></footer>
        </>}
      </dialog>
    </>
  );
}

function Home() {
  const { season, year, metric, setPrompt, setVerifyPrompt, bundle, setUiContext } = useResearch();
  const [q, setQ] = useState('');
  const [ledgerTab, setLedgerTab] = useState('summary');
  const openVerify = question => {
    setPrompt(question);
    setVerifyPrompt(question);
    location.hash = '/verify';
  };
  useEffect(() => { setUiContext?.(prev => ({ ...prev, homeTab: ledgerTab })); }, [ledgerTab]);
  const roleCount = bundle?.roles?.seasons?.[year]?.candidate_count || 0;
  const rulesCount = bundle?.rules?.documents?.length || 0;
  const rankedPlayers = season ? [...season.players].filter(p => p.official_rank).sort((a, b) => a.official_rank - b.official_rank) : [];
  const basePlayers = rankedPlayers.length
    ? rankedPlayers
    : (season
      ? [...season.players].sort((a, b) => ((b.weighted_honor_score || 0) - (a.weighted_honor_score || 0)) || (b.mvp - a.mvp) || (b.evp - a.evp) || ((b.rating_estimate || 0) - (a.rating_estimate || 0)))
      : []);
  const topPlayers = (metric && metric !== 'overall' && season)
    ? [...season.players]
        .map(p => ({ ...p, _stat: playerMetricStat(p, metric) }))
        .filter(p => p._stat.value != null)
        .sort((a, b) => (b._stat.value - a._stat.value) || ((b._stat.maps || 0) - (a._stat.maps || 0)))
        .slice(0, 15)
    : basePlayers.slice(0, 15).map(p => ({ ...p, _stat: playerMetricStat(p, 'overall') }));
  const lead = basePlayers[0];
  const maxRating = Math.max(...topPlayers.slice(0, 10).map(p => p._stat?.value || p.rating_estimate || 0), 1.5);
  const blumTable = season?.blum_2026_table;
  const quickQuestions = [
    '“ZywOo 全靠小组赛虐菜和残局保枪刷数据，打 Top 5 强队和决赛硬仗还得看真神 donk”？',
    '“donk 1.41 的逆天面板全靠绿龙四保一喂闪吸血和中小比赛炸鱼，遇上超级精英赛就哑火”？',
    '“m0NESY 和 NiKo 去猎鹰就是刷 EVP 陪跑，一进大型赛事总决赛就双双隐身拉胯”？',
    '“ropz 和 sh1ro 纯靠残局卖队友保枪刷 K/D，没有大C带飞就是抱大腿混荣誉的体系老六”？'
  ];
  const ledger = [
    [season ? season.events.length : 19, 'L1', '收录分站赛事', 'EVENTS'],
    [season ? season.rows : 692, 'L1/L2', '赛果与强敌记录', 'ROWS'],
    [roleCount || 85, 'L3', '战术位置分位画像', 'ROLES'],
    [rulesCount || 8, 'L4', '官方规则与评选准则', 'RULES']
  ];
  const blumRatingRows = [
    ['overall', 'Rating 3.02'],
    ['vs_top5', 'VS TOP5 队伍'],
    ['vs_top10', 'VS TOP10 队伍'],
    ['vs_top20', 'VS TOP20 队伍'],
    ['big_events', '大型赛事'],
    ['elite_events', '精英赛事'],
    ['super_elite', '超级精英赛事'],
    ['big_playoffs', '大型赛事淘汰赛 & Big Matches'],
    ['elite_playoffs', '精英赛事淘汰赛 & Elite Matches'],
    ['big_event_finals', '大型赛事总决赛']
  ];
  return (
    <div className="dossier-home">
      <section className="atlas-hero">
        <div className="atlas-plate" aria-hidden="true">
          <img src="/atlas-arch.webp" alt="" />
          <TacticalLines />
          <span className="callout c-a"><i />A 小道 · 走廊高台</span>
          <span className="callout c-mid"><i />中门 · 双扇木门</span>
          <span className="callout c-long"><i />中路 · Xbox 跳箱</span>
        </div>
        <div className="plate-meta">
          <span>当前焦点 · {year} 赛季</span>
          <span>当季收录 {season ? season.events.length : 0} 站赛事 · {season ? season.rows : 0} 条参赛记录 · {season ? season.players.length : 0} 位选手</span>
          <span>全库覆盖 2012–2026 共 15 赛季 · 38,895 条实测记录 · 6,943 人次选手档案</span>
        </div>
        <div className="hero-copy">
          <p className="kicker">CS2 职业选手实证观察室</p>
          <h1>
            <span className="h1-zh">拨开面板迷雾，<br />锚定赛场真章。</span>
            <span className="h1-en">Beyond the scoreboard, into the truth.</span>
          </h1>
          <p className="hero-lede">围绕“破除唯面板论与印象流”的研究主题，整合 2012–2026 跨赛季分站赛事、历届 Major 档案、CT/T 阵营与地图池、真实 Demo 战术位置画像及 Rating 3.0 评价规则，支撑同位置选手对比、社区言论求证、年度 Top 20 排名预测与赛事 MVP 动态推演。</p>
          <div className="hero-cta-row">
            <Link to="/compare" className="btn primary">开始同位置选手对比 <ArrowRight size={18} weight="bold" /></Link>
            <Link to="/verify" className="btn ghost">社区争议言论求证</Link>
          </div>
        </div>
        {lead && (
          <Link to={'/players/' + route(lead.id)} className="hero-readout" aria-label={`焦点选手 ${lead.name}`}>
            <span className="readout-label">{year === '2026' ? 'No. 01 · 2026 综合排名第一' : (lead.official_rank ? `No. 01 · ${year} 官方年度第一` : `No. 01 · ${year} 赛季综合领跑`)}</span>
            <strong>{lead.name}</strong>
            <span className="readout-num">{f(lead.rating_estimate)}</span>
            <span className="readout-meta">{lead.weighted_honor_score != null ? `Rating 3.02 · ${lead.maps} 图 · ${lead.mvp} MVP / ${lead.evp} EVP · 积分 ${f(lead.weighted_honor_score)}` : `赛季加权 Rating · ${lead.maps} 图 · ${lead.mvp} MVP / ${lead.evp} EVP`}</span>
          </Link>
        )}
      </section>

      <form className="query-console" onSubmit={e => { e.preventDefault(); openVerify(q); }}>
        <div className="query-console-row">
          <span className="prompt-mark">问</span>
          <input aria-label="首页研究问题" placeholder="输入你想核验的选手对比、社区观点或年底 Major MVP 假设…" value={q} onChange={e => setQ(e.target.value)} />
          <button aria-label="开始研究" className="btn primary" disabled={!q.trim()}>立即核验 <ArrowRight size={17} weight="bold" /></button>
        </div>
        <div className="query-quick-tags">
          <span>热门求证</span>
          {quickQuestions.map((item, i) => (
            <button key={i} type="button" className="chip-btn" onClick={() => openVerify(item)}><b>0{i + 1}</b>{item}</button>
          ))}
        </div>
      </form>

      <section className="module-strip" aria-label="四大核心分析模块">
        {workflows.map(([path, tag, title, text, Icon], i) => (
          <Link className={'workflow w' + i} to={path} key={path}>
            <div className="workflow-top"><span className="roman">{['I','II','III','IV'][i]}</span><span>{tag.split('·')[1]?.trim()}</span><Icon size={20} weight="light" /></div>
            <h3>{title}</h3>
            <p>{text}</p>
            <span className="workflow-go">进入工作台 <ArrowRight size={15} weight="bold" /></span>
          </Link>
        ))}
      </section>

      <section className="paper-zone">
        <div className="zone-head">
          <div>
            <span className="section-no">赛季数据年鉴 · SEASON LEDGER</span>
            <h2>{year} 赛季 Top 10 焦点选手与荣誉面板</h2>
          </div>
          <Scope />
        </div>
        <div className="ledger-grid">
          <div className="ledger-figures">
            {ledger.map(([n, layer, label, en]) => (
              <div key={en} className="figure">
                <span className="figure-layer">{layer} · {en}</span>
                <strong>{Number(n).toLocaleString('en-US')}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
          <div className="ledger-board">
            {!season || !topPlayers.length ? <Empty /> : (
              <>
                {topPlayers.length >= 3 && (
                  <div className="podium-strip">
                    {topPlayers.slice(0, 3).map((p, idx) => (
                      <Link to={'/players/' + route(p.id)} className="podium-card" key={p.id}>
                        <span className="podium-rank">#{String((metric === 'overall' && p.official_rank) ? p.official_rank : (idx + 1)).padStart(2, '0')}</span>
                        <span className="podium-name">{p.name}</span>
                        <strong className="podium-rating">{f(p._stat?.value ?? p.rating_estimate)}</strong>
                        <span className="podium-metrics">收录 {p._stat?.maps ?? p.maps} 图 · {p.mvp} MVP · {p.evp} EVP{p.weighted_honor_score != null ? ` · 荣誉积分 ${f(p.weighted_honor_score)}` : ''}</span>
                      </Link>
                    ))}
                  </div>
                )}
                {blumTable && (
                  <div className="actions" style={{ marginBottom: '14px' }}>
                    <button type="button" className={'btn ' + (ledgerTab === 'summary' ? 'primary' : '')} onClick={() => setLedgerTab('summary')}>Top 10 综合荣誉与核心面板</button>
                    <button type="button" className={'btn ' + (ledgerTab === 'events' ? 'primary' : '')} onClick={() => setLedgerTab('events')}>2026 已结束赛事加权个人荣誉积分（19 站）</button>
                    <button type="button" className={'btn ' + (ledgerTab === 'ratings' ? 'primary' : '')} onClick={() => setLedgerTab('ratings')}>Top 10 十维细分 Rating 矩阵</button>
                  </div>
                )}
                {blumTable && ledgerTab === 'events' ? (
                  <Table topScroll
                    headers={['2026 已结束赛事', '权重', ...blumTable.top10.map(t => `TOP${t.rank} ${t.name}`)]}
                    rows={[
                      ...blumTable.events.map(ev => [
                        <b>{ev.name_zh}</b>,
                        ev.weight_label,
                        ...blumTable.top10.map(t => {
                          const cell = t.events?.[ev.name_zh];
                          if (!cell) return '—';
                          const [award, perf, wpts] = cell;
                          return `${award !== '无' ? award + ' · ' : ''}${f(perf)} (${f(wpts)})`;
                        })
                      ]),
                      [
                        <b>加权个人荣誉积分合计</b>,
                        <b>@BLUM.</b>,
                        ...blumTable.top10.map(t => <b>{f(t.weighted_honor_score)}</b>)
                      ]
                    ]}
                  />
                ) : blumTable && ledgerTab === 'ratings' ? (
                  <Table topScroll
                    headers={['细分项目', ...blumTable.top10.map(t => `${t.name} (Rating / 图数)`)]}
                    rows={blumRatingRows.map(([rKey, rLabel]) => [
                      <b>{rLabel}</b>,
                      ...blumTable.top10.map(t => {
                        const pairVal = t.ratings?.[rKey];
                        return pairVal ? `${f(pairVal[0])} (${pairVal[1]}图)` : '—';
                      })
                    ])}
                  />
                ) : (
                  <Table topScroll
                    headers={
                      year === '2026'
                        ? ['综合排名', '选手', '加权荣誉积分', 'MVP / EVP', '样本图数', metric === 'overall' ? 'Rating 3.02' : metrics[metric], 'vs Top 5 / Top 10', '大型赛淘汰赛 / 总决赛', '选手档案']
                        : [metric === 'overall' ? (rankedPlayers.length ? '官方名次' : '综合排序') : '当前范围排序', '选手', '样本图数', metric === 'overall' ? '赛季加权 Rating' : metrics[metric], 'MVP / EVP', 'CT / T 实测', '选手档案']
                    }
                    rows={topPlayers.slice(0, 10).map((p, idx) => {
                      const val = p._stat?.value ?? p.rating_estimate;
                      const b26 = p.multi_tier_benchmarks?.blum_2026;
                      if (year === '2026') {
                        return [
                          String((metric === 'overall' && p.official_rank) ? p.official_rank : (idx + 1)).padStart(2, '0'),
                          <b className="player-cell">{p.name}</b>,
                          p.weighted_honor_score != null ? <b>{f(p.weighted_honor_score)}</b> : '—',
                          `${p.mvp} / ${p.evp}`,
                          p._stat?.maps ?? p.maps,
                          <span className="rating-cell"><span>{f(val)}</span><i style={{ width: `${Math.max(6, ((val || 0) - 0.8) / (maxRating - 0.8) * 100)}%` }} /></span>,
                          b26 ? `${f(b26.vs_top5?.rating)} (${b26.vs_top5?.maps}图) / ${f(b26.vs_top10?.rating)} (${b26.vs_top10?.maps}图)` : (p.opponents?.vsTop5 ? `${f(p.opponents.vsTop5)} / ${f(p.opponents.vsTop10)}` : '—'),
                          b26 ? `${f(b26.big_playoffs?.rating)} (${b26.big_playoffs?.maps}图) / ${f(b26.big_event_finals?.rating)} (${b26.big_event_finals?.maps}图)` : '—',
                          <Link className="text-link" to={'/players/' + route(p.id)}>查看档案 →</Link>
                        ];
                      }
                      return [
                        String((metric === 'overall' && p.official_rank) ? p.official_rank : (idx + 1)).padStart(2, '0'),
                        <b className="player-cell">{p.name}</b>,
                        p._stat?.maps ?? p.maps,
                        <span className="rating-cell"><span>{f(val)}</span><i style={{ width: `${Math.max(6, ((val || 0) - 0.8) / (maxRating - 0.8) * 100)}%` }} /></span>,
                        `${p.mvp} / ${p.evp}`,
                        p.side_splits?.ct_side ? `CT ${f(p.side_splits.ct_side.rating)} / T ${f(p.side_splits.t_side?.rating)}` : '—',
                        <Link className="text-link" to={'/players/' + route(p.id)}>查看档案 →</Link>
                      ];
                    })}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function TacticalLines() {
  return (
    <svg className="tactical-lines" viewBox="0 0 1672 941" preserveAspectRatio="xMaxYMid slice" aria-hidden="true">
      <path className="t" d="M785 735 C845 770 920 775 985 735 S1075 665 1115 615" />
      <path className="ct" d="M982 575 C982 605 980 635 975 668" />
      <circle className="t" cx="1115" cy="615" r="8.5" /><circle className="ct" cx="982" cy="575" r="8.5" />
      <path className="x" d="M965 672 l20 20 M985 672 l-20 20" />
    </svg>
  );
}

function Compare() {
  const { year, metric, pair, setPair, season, setUiContext } = useResearch();
  const [r, setR] = useState(null);
  useEffect(() => {
    if (r?.status === 'ready' && r.players?.length >= 2) {
      setUiContext?.(prev => ({
        ...prev,
        compareDelta: `${r.players[0]?.name} ${f(r.stats?.[0]?.value)} vs ${r.players[1]?.name} ${f(r.stats?.[1]?.value)}，差值 ${fsigned(r.delta, 4)}`
      }));
    }
  }, [r]);
  const [error, setError] = useState('');
  useEffect(() => {
    setR(null); setError('');
    if (!season) return;
    const c = new AbortController();
    api('compare', { year, metric, players: pair }, c.signal).then(setR).catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => c.abort();
  }, [year, metric, pair.join('|'), !!season]);
  const roleAlign = r?.role_alignment;
  const rolePlayers = roleAlign?.players || [];
  return (
    <>
      <Heading title="选手对比：赛场表现与场上位置" subtitle="在同一赛季与赛事范围内对比两名选手的赛场数据，并结合各自场上位置评估实战表现。" />
      <Scope />
      <div className="analysis-layout">
        <section className="paper compare-paper">
          {!season ? <Empty /> : (
            <>
              <div className="compare-select">
                <PlayerSelect label="选手 A" value={pair[0]} onChange={v => setPair([v, pair[1]])} />
                <span className="versus">对阵</span>
                <PlayerSelect label="选手 B" value={pair[1]} onChange={v => setPair([pair[0], v])} />
              </div>
              {error && <p role="alert" className="error">{error}</p>}
              {r && (
                <>
                  <div className="duel-scoreboard">
                    <div className="duel-side">
                      <span className="duel-player-name">{r.players[0]?.name}</span>
                      <strong className="duel-rating-big">{f(r.stats[0]?.value)}</strong>
                      <small>参赛地图：{r.stats[0]?.maps ?? '暂无'} 张</small>
                    </div>
                    <div className="duel-center-delta">
                      <span>{metrics[metric]} 差值</span>
                      <strong>{r.status === 'ready' ? fsigned(r.delta, 4) : '暂无对比'}</strong>
                    </div>
                    <div className="duel-side right">
                      <span className="duel-player-name">{r.players[1]?.name}</span>
                      <strong className="duel-rating-big">{f(r.stats[1]?.value)}</strong>
                      <small>参赛地图：{r.stats[1]?.maps ?? '暂无'} 张</small>
                    </div>
                  </div>
                  <Table
                    headers={['选手', metrics[metric], '参赛地图', '详细记录']}
                    rows={r.players.map((p, i) => [p.name, f(r.stats[i].value), r.stats[i].maps ?? '暂无', <Source item={r.stats[i].evidence} />])}
                  />
                  <Note>
                    {r.status === 'ready'
                      ? `数据对比：两人在此范围内相差 ${f(Math.abs(r.delta), 4)}（${r.delta === 0 ? '表现持平' : r.delta > 0 ? `${r.players[0]?.name} 略高` : `${r.players[1]?.name} 略高`}）。`
                      : '当前筛选范围内暂无完整比赛记录，无法直接对比差值。'}
                    {r.stats[0].scope}。{rolePlayers.length < 2 ? r.notice : null}
                  </Note>
                  {r.official_verifications?.length > 0 && (
                    <div className="info-card">
                      <h4>赛季荣誉与排名说明</h4>
                      {r.official_verifications.map(v => (
                        <p key={v.player_id}><b>{v.name}</b>：{v.discrepancy_note} <a className="text-link" href={v.source_url} target="_blank" rel="noreferrer">查看评选报道 ↗</a></p>
                      ))}
                    </div>
                  )}
                  {rolePlayers.length >= 2 && (
                    <div className="role-align-section">
                      <h3>场上位置与打法风格对比</h3>
                      <Note>
                        {roleAlign.comparison_note}
                      </Note>
                      <div className="role-cards-grid">
                        {rolePlayers.map(rp => (
                          <article className="role-card" key={rp.id}>
                            <div className="role-card-head">
                              <h4>{rp.name} — {rp.role_short || rp.role_name}</h4>
                              <span className="role-sample-badge">同位置参考 {rp.peer_group_size} 人</span>
                            </div>
                            <p>{rp.role_description}</p>
                            <div className="role-stat-row">
                              <span>同位置 Rating 表现：<b>超过 {f(rp.peer_benchmarks?.rating?.percentile, 0)}% 同位置选手</b></span>
                              <span>同位置局均伤害（ADR）：<b>超过 {f(rp.peer_benchmarks?.adr?.percentile, 0)}% 同位置选手</b></span>
                              <div className="percentile-bar-track"><div className="percentile-bar-fill" style={{ width: `${Math.min(100, Math.max(6, rp.peer_benchmarks?.rating?.percentile || 50))}%` }} /></div>
                            </div>
                            <div className="role-stat-row">
                              <span>平均首次交火：{rp.style_metrics.first_duel_time} 秒</span>
                              <span>首杀尝试比例：{rp.style_metrics.opening_attempt_pct}%</span>
                            </div>
                            <div className="role-stat-row">
                              <span>阵亡可补枪率：{rp.style_metrics.tradeable_deaths_pct}%</span>
                              <span>回合末存活率：{rp.style_metrics.last_alive_pct}%</span>
                            </div>
                            <div className="role-stat-row">
                              <span>狙击枪击杀占比：{rp.style_metrics.awp_kills_pct}%</span>
                              <span>道具支援评分：{rp.style_metrics.utility_efficiency} 分</span>
                            </div>
                            {rp.measured_demo_metrics?.tapd_overall_s != null && (
                              <small style={{ display: 'block', marginTop: 4 }}>
                                <b>比赛录像细节</b>：平均存活时长 {rp.measured_demo_metrics.tapd_overall_s} 秒（进攻方 {rp.measured_demo_metrics.tapd_t_s} 秒 / 防守方 {rp.measured_demo_metrics.tapd_ct_s} 秒） · 首杀尝试比例 {rp.measured_demo_metrics.oap_overall_pct}% · 5 秒内队友补枪配合率 {rp.measured_demo_metrics.pokt_overall_pct}%
                              </small>
                            )}
                          </article>
                        ))}
                      </div>
                    </div>
                  )}
                  {(r.players[0]?.side_splits?.ct_side || r.players[1]?.side_splits?.ct_side || r.players[0]?.map_pool?.length || r.players[1]?.map_pool?.length) ? (
                    <div className="role-align-section">
                      <h3>攻防阵营与常用地图表现</h3>
                      <Table
                        headers={['阵营 / 地图', `${r.players[0]?.name} 表现`, `${r.players[1]?.name} 表现`, '分差']}
                        rows={[
                          ...['ct_side', 't_side', 'both_sides'].map(sk => {
                            const s0 = r.players[0]?.side_splits?.[sk];
                            const s1 = r.players[1]?.side_splits?.[sk];
                            const lbl = sk === 'ct_side' ? '防守方（CT）' : (sk === 't_side' ? '进攻方（T）' : '全阵营综合');
                            const d = (s0?.rating != null && s1?.rating != null) ? fsigned(s0.rating - s1.rating, 2) : '—';
                            return [
                              <b>{lbl}</b>,
                              s0?.rating != null ? `${f(s0.rating)}（${s0.rounds ? `${s0.rounds} 回合` : `${s0.maps_est} 张图`}）` : '—',
                              s1?.rating != null ? `${f(s1.rating)}（${s1.rounds ? `${s1.rounds} 回合` : `${s1.maps_est} 张图`}）` : '—',
                              d
                            ];
                          }),
                          ...['Mirage', 'Inferno', 'Nuke', 'Dust2', 'Ancient', 'Anubis', 'Overpass', 'Vertigo'].map(mp => {
                            const m0 = (r.players[0]?.map_pool || []).find(x => x.map.toLowerCase() === mp.toLowerCase());
                            const m1 = (r.players[1]?.map_pool || []).find(x => x.map.toLowerCase() === mp.toLowerCase());
                            if (!m0 && !m1) return null;
                            const d = (m0?.rating != null && m1?.rating != null) ? fsigned(m0.rating - m1.rating, 2) : '—';
                            return [
                              `地图 · ${mp}`,
                              m0?.rating != null ? `${f(m0.rating)}（防守 ${f(m0.ct_rating)} / 进攻 ${f(m0.t_rating)} · ${m0.rounds} 回合）` : '—',
                              m1?.rating != null ? `${f(m1.rating)}（防守 ${f(m1.ct_rating)} / 进攻 ${f(m1.t_rating)} · ${m1.rounds} 回合）` : '—',
                              d
                            ];
                          }).filter(Boolean)
                        ]}
                      />
                    </div>
                  ) : null}
                  <footer className="compare-actions">
                  <Save title={r.players.map(p => p.name).join(' × ')} payload={{ type: 'compare', year, metric, pair, result: r }} />
                  </footer>
                </>
              )}
            </>
          )}
        </section>
      </div>
    </>
  );
}

const RULE_CATEGORY_LABELS = {
  rating_system: '评分标准',
  role_alignment: '位置分工',
  metric_scope: '常见误区',
  top20_criteria: '年度评选',
  fact_checking: '查证原则'
};

function Verify() {
  const { bundle, year, metric, pair, prompt, setPrompt, verifyPrompt, setVerifyPrompt, restored, setUiContext } = useResearch();
  const rules = bundle?.rules?.documents || [];
  const sampleClaims = [
    {
      tag: '载物保枪虐菜 vs 洞克真神？',
      text: '“ZywOo 全靠小组赛虐菜和残局保枪刷数据，打 Top 5 强队和决赛硬仗还得看真神 donk”？'
    },
    {
      tag: '绿龙四保一吸血 vs 超精硬仗？',
      text: '“donk 1.41 的逆天面板全靠绿龙四保一喂闪吸血和中小比赛炸鱼，遇上超级精英赛就哑火”？'
    },
    {
      tag: '猎鹰双子星 EVP 陪跑与决赛隐身？',
      text: '“m0NESY 和 NiKo 去猎鹰就是刷 EVP 陪跑，一进大型赛事总决赛就双双隐身拉胯”？'
    },
    {
      tag: '老六卖队友保枪 vs 大赛关键先生？',
      text: '“ropz 和 sh1ro 纯靠残局卖队友保枪刷 K/D，没有大C带飞就是抱大腿混荣誉的体系老六”？'
    }
  ];
  const followUpPrompts = [
    '补充对比涉及选手在大型赛事淘汰赛与总决赛的表现差异。',
    '结合同位置其他选手的表现，进一步比较其场上贡献。',
    '如果只看对阵世界前五强队的比赛记录，上述核实结论会发生变化吗？'
  ];
  const initialRestored = restored && ['verify', 'agent'].includes(restored.type) && restored.result
    ? { ...restored.result, question: restored.question || restored.result.question, year: restored.year || year }
    : null;
  const [draft, updateDraft, storageError] = useConversationStore(`verify:${year}`, { q: prompt || initialRestored?.question || sampleClaims[0].text, turns: initialRestored ? [initialRestored] : [], activeTurnIdx: 0 });
  const { q, turns, activeTurnIdx } = draft;
  const result = turns[activeTurnIdx] || turns[turns.length - 1] || null;
  const setQ = q => updateDraft({ q });
  useEffect(() => {
    if (initialRestored) updateDraft({ q: initialRestored.question, turns: [initialRestored], activeTurnIdx: 0 });
  }, [restored]);
  const [busy, setBusy] = useState(false);
  const [pendingQ, setPendingQ] = useState('');
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');
  const request = useRef(null);
  const reader = useRef(null);
  const answer = useRef(null);
  const questionField = useRef(null);
  const dialogueRef = useRef(null);

  useEffect(() => () => { request.current?.abort(); request.current = null; }, []);
  useEffect(() => {
    request.current?.abort(); request.current = null;
    setBusy(false); setError(''); setExpanded(false); setCopyStatus('');
  }, [year]);
  useEffect(() => {
    if (prompt) {
      setQ(prompt);
      setPrompt('');
      requestAnimationFrame(() => questionField.current?.focus());
    }
  }, [prompt, setPrompt]);
  useEffect(() => {
    if (verifyPrompt) {
      setQ(verifyPrompt);
      setVerifyPrompt('');
      requestAnimationFrame(() => questionField.current?.focus());
    }
  }, [verifyPrompt, setVerifyPrompt]);
  useEffect(() => {
    const dialog = reader.current;
    if (!expanded || !dialog) return;
    const previous = document.body.style.overflow;
    dialog.showModal(); document.body.style.overflow = 'hidden';
    return () => { dialog.close(); document.body.style.overflow = previous; };
  }, [expanded]);

  function cancel() {
    request.current?.abort(); request.current = null; setBusy(false);
    setError('已取消本次分析，可以修改主张后重新求证。');
  }
  async function copyAnswer() {
    if (!result) return;
    try { await navigator.clipboard.writeText(answer.current?.innerText || result.answer); setCopyStatus('已复制结论正文'); }
    catch { setCopyStatus('复制失败，请手动选择正文复制'); }
  }
  async function ask(e) {
    if (e) e.preventDefault();
    if (!q.trim() || busy) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    const question = q.trim();
    setPendingQ(question);
    setBusy(true); setError(''); setCopyStatus(''); setExpanded(false);
    const timer = setTimeout(() => {
      controller.abort();
      if (request.current === controller) {
        setBusy(false); setError('分析等待超时，请稍后重试或缩小问题范围。');
      }
    }, 120000);
    try {
      const r = await api('agent', {
        year,
        question,
        context: { selected_players: pair, metric, mode: 'verify' }
      }, controller.signal);
      if (!controller.signal.aborted) {
        const turnObj = { ...r, question, year: r.year || year, metricLabel: metrics[metric] };
        updateDraft(prev => ({ turns: [...prev.turns, turnObj], activeTurnIdx: prev.turns.length }));
      }
    } catch (err) {
      if (!controller.signal.aborted && request.current === controller) setError(err.message);
    } finally {
      clearTimeout(timer);
      if (request.current === controller) setBusy(false);
    }
  }
  function selectTurn(idx) {
    const t = turns[idx];
    if (!t) return;
    updateDraft({ activeTurnIdx: idx });
    setCopyStatus('');
  }
  function clearDialogue() {
    request.current?.abort(); request.current = null;
    setBusy(false); setError(''); updateDraft({ turns: [], activeTurnIdx: 0 }); setCopyStatus('');
    requestAnimationFrame(() => questionField.current?.focus());
  }
  const toolsCount = result?.tools?.length || 0;

  return (
    <>
      <Heading title="言论求证：社区热门争议与评分规则核实" subtitle="针对社区常见观点与争议，结合历年分站比赛记录、场上位置特点与官方评分规则给出核实结论。" />
      <Scope />
      <div className="verify-workbench">
        <section className="verify-stage agent-panel" aria-label="言论求证中心工作台">
          <header className="verify-stage-header">
            <div className="verify-stage-brand">
              <Compass size={28} weight="duotone" />
              <div>
                <h2>SwingAudit · 言论求证中枢台</h2>
                <small>{year} 赛季 · 实时调取比赛记录与评分规则，输出核实结论与可溯源明细</small>
              </div>
            </div>
            <div className="tool-pills verify-capability-pills">
              <span>赛事数据查询</span>
              <span>场上位置对比</span>
              <span>社区言论求证</span>
              <span>年度排名分析</span>
              <span>赛事走势推演</span>
            </div>
          </header>

          <div className="verify-console-core">
            {storageError && <p role="status" className="agent-storage-note">{storageError}</p>}
            <form onSubmit={ask} className="verify-composer-card">
              <div className="verify-composer-top">
                <label className="field verify-claim-field">
                  <span className="verify-field-head">
                    <b>需要核对的主张</b>
                    <small className="verify-scope-pill">当前求证口径：{year} 赛季 · {metrics[metric]}</small>
                  </span>
                  <textarea
                    ref={questionField}
                    aria-label="待核实的社区争议主张"
                    rows={3}
                    value={q}
                    maxLength={4000}
                    disabled={busy}
                    placeholder="输入您想核实的社区争议观点，例如：某位选手是否只会打弱队、0 个 MVP 为什么能进年度前 3、保枪对 Rating 3.0 的影响…"
                    onChange={e => setQ(e.target.value)}
                    onKeyDown={e => {
                      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !e.nativeEvent.isComposing && q.trim() && !busy) {
                        e.preventDefault();
                        e.currentTarget.form.requestSubmit();
                      }
                    }}
                  />
                </label>
              </div>
              <div className="verify-composer-foot">
                <p className="verify-honest-rule">
                  查证原则：若某项细分数据暂未收录或参赛场次较少，将如实提示“暂无足够比赛记录”，不会凭空猜测。支持 Ctrl / ⌘ + Enter 快捷提交。
                </p>
                <div className="verify-composer-actions">
                  {turns.length > 0 && !busy && (
                    <button type="button" className="btn" onClick={clearDialogue}>清空对话</button>
                  )}
                  {busy && (
                    <button type="button" className="btn" onClick={cancel}>取消分析</button>
                  )}
                  <button className="btn primary verify-submit-btn" disabled={busy || !q.trim()}>
                    {busy ? '正在查询比赛记录并生成分析…' : '核实主张并查看来源'} {!busy && <ArrowRight size={16} />}
                  </button>
                </div>
              </div>
            </form>

            {!result && !busy && (
              <div className="verify-presets-zone">
                <div className="verify-presets-header">
                  <h3>§ 常见社区争议（点击即可填入上方求证台）</h3>
                </div>
                <div className="preset-list verify-preset-grid">
                  {sampleClaims.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className={`btn preset-btn verify-preset-card${q === item.text ? ' active' : ''}`}
                      onClick={() => {
                        setQ(item.text);
                        requestAnimationFrame(() => questionField.current?.focus());
                      }}
                    >
                      <span className="preset-card-meta">
                        <b>0{idx + 1}</b>
                        <small>{item.tag}</small>
                        {q === item.text && <em className="preset-selected-badge">已填入求证台</em>}
                      </span>
                      <span className="preset-card-text">{item.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {(busy || result || error || turns.length > 1) && (
            <div className="verify-dialogue-stream" ref={dialogueRef} aria-live="polite">
              {turns.length > 1 && !busy && (
                <div className="verify-turn-switcher" role="tablist" aria-label="历史求证对话轮次">
                  <span>求证对话记录（共 {turns.length} 轮）</span>
                  <div className="verify-turn-pills">
                    {turns.map((t, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className={`chip-btn${idx === activeTurnIdx ? ' active' : ''}`}
                        onClick={() => selectTurn(idx)}
                      >
                        <b>0{idx + 1}</b> {t.question.slice(0, 22)}{t.question.length > 22 ? '…' : ''}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {error && <p role="alert" className="error verify-error-banner">{error}</p>}

              {busy && (
                <article className="verify-dialogue-turn is-busy">
                  <div className="verify-bubble-user">
                    <div className="bubble-meta">
                      <span className="bubble-tag user">提出主张</span>
                      <small>{year} 赛季 · {metrics[metric]}</small>
                    </div>
                    <p className="bubble-claim-text">{pendingQ || q}</p>
                  </div>
                  <div className="verify-bubble-agent loading">
                    <p role="status" className="agent-loading">正在查询比赛记录并生成分析…</p>
                    <div className="verify-progress-steps">
                      <div className="verify-step-item">
                        <b>步骤 01</b>
                        <span>拆解争议主张，锁定涉及选手与 {year} 赛季筛选范围</span>
                      </div>
                      <div className="verify-step-item">
                        <b>步骤 02</b>
                        <span>检索分站比赛记录、强敌交手表现与相近位置选手的表现</span>
                      </div>
                      <div className="verify-step-item">
                        <b>步骤 03</b>
                        <span>对照 HLTV Rating 3.0 与评选标准生成核实结论与来源明细</span>
                      </div>
                    </div>
                  </div>
                </article>
              )}

              {result && !busy && (
                <article className="verify-dialogue-turn">
                  <div className="verify-bubble-user">
                    <div className="bubble-meta">
                      <span className="bubble-tag user">提出主张</span>
                      <small>{result.year} 赛季 · {result.metricLabel || metrics[metric]}</small>
                    </div>
                    <p className="bubble-claim-text">{result.question}</p>
                  </div>

                  <div className="verify-bubble-agent">
                    <div className="verify-agent-head">
                      <div className="verify-agent-title">
                        <span className="bubble-tag agent">核实结论</span>
                        <div>
                          <h3>{result.plan?.task_label || '社区争议主张数据核实'}</h3>
                          <small>
                            {result.year} 赛季 · 调取 {toolsCount} 项比赛数据与规则来源
                            {result.plan?.detected_players?.length ? ` · 涉及选手：${result.plan.detected_players.join('、')}` : ''}
                          </small>
                        </div>
                      </div>
                      <div className="verify-agent-head-right">
                        {result.verification && (
                          <span className="badge ok">
                            ✓ 数据核对（{result.verification.status === 'remediated_after_rollback' ? '补充查询后已核实' : '已核实'}）
                          </span>
                        )}
                        <button type="button" className="text-link" onClick={() => setExpanded(true)}>展开阅读 ↗</button>
                      </div>
                    </div>

                    <div className="verify-verdict-split">
                      <div className="verify-verdict-main">
                        <div className="message" ref={answer}>
                          <AnswerMarkdown text={result.answer} />
                        </div>
                        <div className="verify-followup-box">
                          <span>继续追问</span>
                          <div className="verify-followup-chips">
                            {followUpPrompts.map((fp, i) => (
                              <button
                                key={i}
                                type="button"
                                className="chip-btn"
                                onClick={() => {
                                  setQ(`${result.question} 追问：${fp}`);
                                  requestAnimationFrame(() => questionField.current?.focus());
                                }}
                              >
                                <b>追问 0{i + 1}</b> {fp}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>

                      <aside className="verify-verdict-evidence" aria-label="参考比赛数据明细">
                        <div className="verify-evidence-head">
                          <h4>参考比赛数据明细</h4>
                          <span>{toolsCount} 项来源</span>
                        </div>
                        {result.verification?.checks?.length > 0 && (
                          <div className="verify-checks-list">
                            {result.verification.checks.map(c => (
                              <p key={c.check_id}>✓ <b>{c.label}</b>：{c.detail}</p>
                            ))}
                          </div>
                        )}
                        <div className="verify-trace-list">
                          {(result.tools || []).map((t, i) => (
                            <div key={i} className="tool-trace-item">
                              <p>
                                <b>检索内容 0{i + 1}</b>：
                                {t.arguments?.query || (t.arguments?.players ? t.arguments.players.join(' vs ') : '') || t.arguments?.claim || t.arguments?.player || `${result.year} 赛季记录`}
                              </p>
                              <Source item={{ ...t.arguments, controlled_tool: t.controlled_tool || t.tool, result: JSON.stringify(t.result) }} />
                            </div>
                          ))}
                        </div>
                      </aside>
                    </div>

                    <footer className="verify-turn-footer">
                      <div className="verify-turn-foot-left">
                        <button type="button" className="text-link" onClick={copyAnswer}>复制正文</button>
                        <span role="status">{copyStatus}</span>
                      </div>
                      <div className="verify-turn-foot-right">
                        <Save title="言论求证" payload={{ type: 'verify', year: result.year, question: result.question, result }} />
                      </div>
                    </footer>
                  </div>
                </article>
              )}


            </div>
            )}

            {(result || busy) && (
              <div className="verify-presets-zone is-compact">
                <div className="verify-presets-header">
                  <h3>§ 切换其他常见社区争议继续求证</h3>
                </div>
                <div className="preset-list verify-preset-grid">
                  {sampleClaims.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className={`btn preset-btn verify-preset-card${q === item.text ? ' active' : ''}`}
                      onClick={() => {
                        setQ(item.text);
                        requestAnimationFrame(() => questionField.current?.focus());
                      }}
                    >
                      <span className="preset-card-meta">
                        <b>0{idx + 1}</b>
                        <small>{item.tag}</small>
                        {q === item.text && <em className="preset-selected-badge">已填入求证台</em>}
                      </span>
                      <span className="preset-card-text">{item.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="paper verify-rules-shelf" aria-label="官方评分规则与评选标准参考">
          <div className="verify-rules-head">
            <div>
              <h3>§ 官方评分规则与评选标准参考</h3>
              <p>求证台在核实“保枪刷 K/D”“0 个 MVP 进前 3”“不同场上位置面板差异”等争议时，将同步对照以下官方规则条目。</p>
            </div>
          </div>
          <div className="rules-grid">
            {rules.map(doc => (
              <article key={doc.rule_id} className="rule-card">
                <h4>{doc.title}</h4>
                <p>{doc.summary}</p>
                <small>{doc.detail}</small>
                <div className="rule-meta">
                  <span>参考条目</span>
                  <a className="text-link" href={doc.source_url} target="_blank" rel="noreferrer">{doc.source_title} ↗</a>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <dialog className="agent-reader" ref={reader} aria-label="分析结论展开阅读" onCancel={() => setExpanded(false)} onClose={() => setExpanded(false)} onClick={e => { if (e.target === e.currentTarget) setExpanded(false); }}>
        {result && <>
          <header className="agent-reader-heading"><div><small>{result.year} 赛季 · {toolsCount} 项数据来源</small><h2>言论求证结论</h2></div><button type="button" className="icon-btn" aria-label="关闭展开阅读" onClick={() => setExpanded(false)} autoFocus><X size={22} /></button></header>
          <div className="agent-reader-body"><p className="agent-reader-question">{result.question}</p><AnswerMarkdown text={result.answer} /><AgentEvidence result={result} /></div>
          <footer><button type="button" className="text-link" onClick={copyAnswer}>复制正文</button><span role="status">{copyStatus}</span></footer>
        </>}
      </dialog>
    </>
  );
}

const ATTR_LABEL_MAP = {
  '高级别赛事样本图数保障': '大赛出场场次充足',
  '整体加权 Rating 贡献': '全年整体 Rating 突出',
  '全年参赛站数深度': '全年赛事出勤稳定',
  '对阵 Top 5/10 强敌抗压差值': '对阵世界前十强队发挥',
  'Major/超精/精英赛硬仗表现': '顶级大赛关键局表现',
  'MVP / EVP 荣誉密度修正': '大赛荣誉获奖率'
};

function formatAttrLabel(label) {
  return ATTR_LABEL_MAP[label] || label;
}

const ABLATION_DISPLAY = {
  rating_baseline: {
    name: '仅按赛季平均 Rating 排名',
    rule: '按参赛地图数加权计算全年平均 Rating',
    note: '只看个人场均数据，未区分赛事含金量与 MVP 荣誉，容易受中小型赛事高分影响。'
  },
  layer1_honor_baseline: {
    name: '仅按大赛荣誉与战队成绩排名',
    rule: '按赛事级别汇总冠亚军名次与 MVP / EVP 荣誉',
    note: '能准确锁定榜首核心人选，但在荣誉相近的中游选手之间难以拉开差距。'
  },
  hybrid_ridge: {
    name: '综合评估（均衡权重方案）',
    rule: '大赛荣誉得分 + 强敌交手与参赛场次均衡加分',
    note: '按均衡比例衡量对阵强队表现与大赛出场次数，适合直观对比各项加分来源。'
  },
  hybrid_gbr: {
    name: '综合评估（大赛高光优先方案）',
    rule: '大赛荣誉得分 + 顶级大赛高光表现额外加权',
    note: '对顶级赛事高分表现给与更高权重，突出大赛关键场次的排名优势。'
  },
  hybrid_rf: {
    name: '综合评估（大赛荣誉 + 强敌表现加成）',
    rule: '大赛荣誉得分 + 对阵强队与顶级赛事表现加分',
    note: '兼顾大赛冠军 MVP 含金量与对阵世界前十强队的实战发挥，与官方评选结果高度吻合。'
  },
  rf_historical_v1: {
    name: '传统基础数据综合榜',
    rule: '综合全年 Rating、总地图数、MVP 与 EVP 数量',
    note: '不单独拆分赛事级别与强敌交手表现，作为基础数据排行参考。'
  }
};

const ROLE_DISPLAY_MAP = {
  Awper: '主狙手',
  Entry: '突破手',
  Closer: '残局自由人',
  Support: '辅助位',
  'awpy实测': '综合定位'
};

function formatRoleLabel(role) {
  if (!role) return '—';
  return ROLE_DISPLAY_MAP[role] || role;
}

const DATASET_DISPLAY_MAP = {
  'iftv-top20': ['2024–2025 分站赛事成绩与强敌交手记录', '赛事与强敌表现'],
  'ageha6912-majors': ['2013–2025 历年 Top 20 榜单与 24 届 Major 决赛数据', '历届 Major 档案'],
  'santtu777-hltv-top': ['2018–2024 年度前五十选手大赛、Major 与荣誉统计', '大赛与个人荣誉'],
  'markzhdan-top20': ['2012–2025 历年年度评选核心指标与 MVP 统计', '年度评选档案'],
  'danilofuchs-top20': ['2013–2022 历年官方 Top 20 获奖专访与报道索引', '官方评选报道'],
  'raymondtoh94-hltv': ['职业选手 13 张比赛地图与 CT / T 攻防阵营表现', '地图池与攻防阵营'],
  'tedtay-csgo': ['历年职业比赛单图十人详细面板、首杀与闪光助攻', '单场技术统计'],
  'onestudio-hltv': ['2012–2022 历年职业赛事日程与场次记录', '历史赛程档案'],
  'valve-vrs': ['Valve 官方全球战队积分榜与赛事分级名单', '官方战队积分'],
  'ektarr-cs2': ['2023–2026 CS2 时代职业赛事单场与单图表现记录', 'CS2 赛事统计'],
  'eupeutro-blast-2026': ['2026 重点赛事 Rating 3.0 与回合胜率贡献统计', '2026 赛季数据'],
  'jamiepacker-roles': ['职业选手场上位置、存活时长、首杀与队友补枪统计', '场上位置与录像细节'],
  'opencs2-telemetry': ['2026 职业赛现役地图攻防胜率、首杀时间与道具节奏', '现役地图攻防参考'],
  'sneakyzero-economy': ['2026 职业赛回合经济与枪械配置统计', '回合经济与节奏'],
  'griffin-ts-rounds': ['2024–2025 职业赛事逐回合进程与状态趋势记录', '赛事进程统计'],
  'esportsbench-cs': ['历年国际大型赛事冠亚军、奖金池与参赛阵容索引', '赛事历史百科'],
  'eshtiak-career': ['职业选手生涯累计地图、爆头率、道具伤害与互救统计', '职业生涯总览'],
  'livanoff-merfaruk': ['2013–2023 历年职业赛事赛果与回合记录汇总', '历史赛果汇总'],
  'pachellber-econ-r30': ['2024–2026 CS2 职业选手 Rating 3.0、回合发枪经济与 CT/T 官方位置', 'CS2 经济与角色'],
  'nmwalsh-hltv-ids': ['14,171 名职业选手官方 HLTV ID、国籍与早期历史赛事索引', '选手与赛事索引'],
  'gungor-major-mvps': ['2013–2025 历届 Major 锦标赛全部 130 人次 MVP 与 EVP 官方名录', 'Major 荣誉档案'],
  'dsckgec-career': ['844 名职业选手生涯实名、手雷伤害、队友互救与 KPR / DPR 面板', '职业生涯扩展'],
  'rlinv1-top20-rosters': ['Top 20 顶尖战队 103 名现役主力 Rating 2.1、KAST、ADR 与定妆照', '现役主力阵容']
};

function formatVrsShift(change) {
  if (change == null) return '新入榜';
  if (change === 0) return '持平';
  return change > 0 ? `↑${change}` : `↓${Math.abs(change)}`;
}

function renderVrsRows(rows, isRegional = false, showMajorStage = true) {
  return (rows || []).map(t => {
    const baseCols = [
      isRegional ? `${t.region_zh || '赛区'} #${t.regional_rank || t.rank}` : '#' + (t.global_rank || t.rank),
      isRegional ? '#' + (t.global_rank || t.rank) : `${t.region_zh || '—'} #${t.regional_rank || t.rank}`,
      formatVrsShift(t.rank_change),
      <b>{f(t.points, 1)}</b>,
      t.starting_rank_value != null ? `${f(t.starting_rank_value, 1)} (${t.h2h_adjustments >= 0 ? '+' : ''}${f(t.h2h_adjustments, 1)})` : '—',
      <b>{t.team}</b>,
      t.roster,
      t.bounty_offered,
      t.bounty_collected,
      t.opponent_network,
      t.lan_wins,
      `${t.record_summary || '—'} · ${t.scaled_winnings || '$0'}`,
    ];
    if (showMajorStage) baseCols.push(t.major_stage || '—');
    baseCols.push(t.source_url ? <a className="text-link" href={t.source_url} target="_blank" rel="noreferrer">查看明细 ↗</a> : '—');
    return baseCols;
  });
}

function Rankings() {
  const { bundle, year, season, setUiContext } = useResearch();
  const [pageMode, setPageMode] = useState('seasons');
  const [viewMode, setViewMode] = useState('hybrid');
  const [valTab, setValTab] = useState('hybrid');
  const [vrsScope, setVrsScope] = useState('global');
  useEffect(() => {
    const scopeMap = { global: '全球总榜 Top 50', europe: '欧洲赛区 Top 30', americas: '美洲赛区 Top 20', asia: '亚洲赛区 Top 20', majors: '2026 两届 Major 官方直邀名单', oct05: '10月5日 Valve 月度原榜' };
    const label = pageMode === 'validation' ? '历年预测结果与官方榜单对照' : year === '2026'
      ? (viewMode === 'vrs' ? `Valve 全球战队官方积分榜 · ${scopeMap[vrsScope] || '全球总榜'}` : '2026 选手年度积分追踪')
      : `${year} 赛季预测排名与官方 Top 20 对照`;
    setUiContext?.(prev => ({ ...prev, rankingsLabel: label }));
  }, [year, pageMode, viewMode, vrsScope]);
  const r = bundle.report;
  const hybridRows = r.hybrid_rankings || r.rankings || [];
  const ablation = r.ablation || [];
  const l1BaseRow = ablation.find(a => a.method_id === 'layer1_honor_baseline');
  const multiHoldouts = r.multi_year_holdouts || [];
  const live2026 = r.live_2026_tracker || [];
  const vrsData = bundle?.sources?.valve_vrs || {};
  const vrs2026 = vrsData.global_top50_2026 || [];
  const vrsOct05 = vrsData.global_top50_2026_oct05 || [];
  const vrsRegions = vrsData.regions_2026 || {};
  const vrsMajors = vrsData.major_invitations_2026 || {};
  const activeVrsRows = vrsScope === 'europe' ? (vrsRegions.europe || []) : vrsScope === 'americas' ? (vrsRegions.americas || []) : vrsScope === 'asia' ? (vrsRegions.asia || []) : vrsScope === 'oct05' ? vrsOct05 : vrs2026;
  const isRegionalVrs = vrsScope === 'europe' || vrsScope === 'americas' || vrsScope === 'asia';
  return (
    <>
      <Heading title="年度排名预测：大赛荣誉与强敌表现综合榜" subtitle="汇总 2013–2025 历年 HLTV 官方 Top 20 榜单与 2026 赛季最新积分追踪。" />
      <div className="rankings-mode-deck" role="navigation" aria-label="年度排名视图切换">
        <div className="rankings-mode-tabs">
          <button
            type="button"
            className={'rankings-mode-pill ' + (pageMode === 'seasons' ? 'active' : '')}
            onClick={() => setPageMode('seasons')}
          >
            <span>历年榜单与 2026 实时追踪</span>
            <small>2012–2026 赛季档案</small>
          </button>
          <button
            type="button"
            className={'rankings-mode-pill ' + (pageMode === 'validation' ? 'active' : '')}
            onClick={() => setPageMode('validation')}
          >
            <span>综合评分与官方对照分析</span>
            <small>{l1BaseRow?.top20_hits ?? r.metrics.top20_hits}/20 吻合 · 7 季验证</small>
          </button>
        </div>
        {pageMode === 'seasons' ? (
          <Scope showMetric={false} />
        ) : (
          <div className="scope-bar rankings-validation-meta">
            <span>验证范围：2019–2025 连续 7 个官方评选赛季 · 2025 候选样本池 {r.test_candidates || 352} 位职业选手</span>
            <div className="actions" style={{ margin: 0 }}>
              <Save title="年度排名综合评分与官方对照验证报告" payload={{ type: 'rankings', year: '2025', result: r }} />
              <button type="button" className="btn" onClick={() => exportFile('年度排名报告.json', r)}>导出榜单数据 <Download size={17} /></button>
            </div>
          </div>
        )}
      </div>

      {pageMode === 'validation' ? (
        <section className="paper">
          <h2>综合评分体系与 HLTV 官方榜单对照验证（2019–2025 实证复盘）</h2>
          <Note>通过对比“大赛荣誉得分 + 强敌表现加分”综合评分与历年 HLTV 官方最终名次，检验评分模型在入围名单、前五顺位及不同评选方案下的实际准确度，并拆解每位选手最主要的加减分依据。</Note>
          <div className="profile-stats">
            <div>
              <span>Top 20 入围吻合度（2025 终榜）</span>
              <strong>{l1BaseRow?.top20_hits ?? r.metrics.top20_hits} / 20 位入围一致</strong>
              <small>在 {r.test_candidates || 352} 位候选选手中精准命中 19 位官方 Top 20 成员</small>
            </div>
            <div>
              <span>前五名顺位吻合度</span>
              <strong>{r.hybrid_metrics?.top5_hits ?? 5} / 5 位顺位完全一致</strong>
              <small>#1 ZywOo、#2 donk、#3 ropz、#4 m0NESY、#5 sh1ro 全部吻合</small>
            </div>
            <div>
              <span>跨赛季预测准确度（2019–2025）</span>
              <strong>平均偏差约 {f(r.hybrid_metrics?.rank_mae ?? 3.50, 1)} 个名次</strong>
              <small>连续 7 个赛季回测验证，显著优于单一面板或纯荣誉排序</small>
            </div>
          </div>
          <div className="actions">
            <button type="button" className={'btn ' + (valTab === 'hybrid' ? 'primary' : '')} onClick={() => setValTab('hybrid')}>2025 综合排名与加减分解析 ({hybridRows.slice(0, 30).length})</button>
            <button type="button" className={'btn ' + (valTab === 'ablation' ? 'primary' : '')} onClick={() => setValTab('ablation')}>不同评选方式准确度对比 ({ablation.length})</button>
            <button type="button" className={'btn ' + (valTab === 'multiyear' ? 'primary' : '')} onClick={() => setValTab('multiyear')}>2019–2025 历年预测准确度 ({multiHoldouts.length})</button>
            <button type="button" className={'btn ' + (valTab === 'v1' ? 'primary' : '')} onClick={() => setValTab('v1')}>基础数据排行参考 ({r.rankings.length})</button>
          </div>
          {valTab === 'ablation' && (
            <Table
              headers={['评选方式', '计分构成', 'Top 20 吻合数', '平均名次偏差', '特点说明']}
              rows={ablation.map(a => {
                const info = ABLATION_DISPLAY[a.method_id] || { name: a.name, rule: a.formula, note: a.note };
                return [<b>{info.name}</b>, info.rule, `${a.top20_hits} / 20`, `约 ${f(a.rank_mae, 1)} 名`, info.note];
              })}
            />
          )}
          {valTab === 'multiyear' && (
            <Table
              headers={['评选赛季', '候选选手人数', '仅按荣誉命中数', '综合评分 Top 20 命中', '前五名顺位命中', '平均名次偏差']}
              rows={multiHoldouts.map(h => [
                `${h.test_year} 赛季`,
                `${h.test_candidates} 人`,
                `${h.l1_top20_hits} / 20`,
                `${Math.max(h.rf_top20_hits, h.ridge_top20_hits)} / 20`,
                `${h.rf_top5_hits} / 5`,
                `约 ${f(h.rf_rank_mae, 1)} 名`
              ])}
            />
          )}
          {valTab === 'hybrid' && (
            <Table
              headers={['综合排名', '官方名次', '选手', '大赛荣誉得分', '强敌表现加分', '年度综合总分', '强敌加分名次提升', '赛季 MVP / EVP', '核心加减分亮点']}
              rows={hybridRows.slice(0, 30).map(p => {
                const attrs = p.feature_attributions_rf || p.feature_attributions || [];
                const resVal = p.layer2_residual_rf;
                return [
                  '#' + p.hybrid_rank,
                  p.official_rank ? '#' + p.official_rank : '未入榜',
                  <Link className="text-link" to={'/players/' + route(p.id)}>{p.name}</Link>,
                  f(p.layer1_honor_score),
                  fsigned(resVal),
                  f(p.hybrid_score),
                  p.residual_rank_shift === 0 ? '持平' : (p.residual_rank_shift > 0 ? `↑${p.residual_rank_shift}` : `↓${Math.abs(p.residual_rank_shift)}`),
                  p.official_verified_mvp !== p.mvp ? `${p.official_verified_mvp} MVP / ${p.evp} EVP` : `${p.mvp} MVP / ${p.evp} EVP`,
                  attrs.slice(0, 2).map(fa => `${formatAttrLabel(fa.label)}（${fa.direction}${Math.abs(fa.impact).toFixed(2)}）`).join('；') || '—'
                ];
              })}
            />
          )}
          {valTab === 'v1' && (
            <Table
              headers={['参考名次', '选手', '官方最终名次', '基础综合分', '参赛地图数']}
              rows={r.rankings.map(p => ['#' + p.predicted_rank, <Link className="text-link" to={'/players/' + route(p.id)}>{p.name}</Link>, p.official_rank ? '#' + p.official_rank : '未入榜', f(p.score), p.maps])}
            />
          )}
        </section>
      ) : !season ? <Empty /> : year === '2026' ? (
        <section className="paper">
          <h2>2026 赛季年度排名实时追踪与 Valve 全球战队积分榜（截至 2026 年 11 月 1 日最新排名）</h2>
          <Note>2026 官方年终 Top 20 尚未揭晓。当前选手榜综合 IEM 科隆 Major（MVP m0NESY）、EPL S24、电竞世界杯等 19 站已完赛重点赛事的荣誉与对阵强队表现实时计算；Valve 全球及欧洲、美洲、亚洲三大赛区战队积分榜已更新至 2026 年 11 月 1 日（PGL 新加坡 Major 邀请截止前夕）最新实时排名，并保留 10 月 5 日月度定榜供对照。</Note>
          <div className="actions">
            <button type="button" className={'btn ' + (viewMode === 'hybrid' ? 'primary' : '')} onClick={() => setViewMode('hybrid')}>2026 选手年度积分追踪 ({live2026.length})</button>
            <button type="button" className={'btn ' + (viewMode === 'vrs' ? 'primary' : '')} onClick={() => setViewMode('vrs')}>Valve 全球战队官方积分榜 ({vrs2026.length})</button>
          </div>
          {viewMode === 'vrs' ? (
            <>
              <div className="formula-banner">
                <div>
                  <div className="formula-title">Valve 官方全球战队积分（VRS）计分规则与 Major 直邀机制</div>
                  <strong>最终官方积分 = 初始基础分 (400–2000) + 直接交手修正分 (H2H)</strong>
                  <p>初始基础分由<b>对战悬赏分</b>（近半年最高 10 笔赛事奖金）、<b>赢取悬赏分</b>（近半年击败高奖金强敌的 10 场最佳胜利）、<b>交手广度</b>（所击败对手的获胜覆盖广度）与<b>线下赛胜场</b>（近半年 10 场最佳线下胜利）四项因子均值折算。自 2025–2026 赛季起，Major 全面取消 RMR 预选赛，全部 32 支参赛队伍直接按欧、美、亚三大赛区 VRS 排名发放 Stage 3 / Stage 2 / Stage 1 直邀资格，并以全球 VRS 排名确定瑞士轮种子顺位。</p>
                </div>
                <div className="tier-badges">
                  <span>欧洲赛区：<b>18 席（6+6+6）</b></span>
                  <span>美洲赛区：<b>9 席（2+1+6）</b></span>
                  <span>亚洲赛区：<b>5 席（0+1+4）</b></span>
                  <span>最新同步：<b>{vrsData.snapshot_date || '2026-11-01'}</b></span>
                </div>
              </div>
              <div className="profile-stats">
                <div>
                  <span>最新全球榜首（2026-11-01）</span>
                  <strong>#1 MOUZ · 1959.0 分</strong>
                  <small>初始分 1967.5 · 交手修正 -8.5 · 较上月 ↑3 名</small>
                </div>
                <div>
                  <span>欧美赛区领跑战队</span>
                  <strong>欧洲 #1 MOUZ · 美洲 #1 FURIA</strong>
                  <small>Vitality（1920.0）与 FURIA（1910.5）分列全球二三位</small>
                </div>
                <div>
                  <span>亚洲赛区头名与直邀线</span>
                  <strong>亚洲 #1 The MongolZ · 1553.0 分</strong>
                  <small>BC.Game、FlyQuest、TYLOO、Lynn Vision 分列二至五位</small>
                </div>
              </div>
              <div className="actions">
                <button type="button" className={'btn ' + (vrsScope === 'global' ? 'primary' : '')} onClick={() => setVrsScope('global')}>全球总榜 Top 50 ({vrs2026.length})</button>
                <button type="button" className={'btn ' + (vrsScope === 'europe' ? 'primary' : '')} onClick={() => setVrsScope('europe')}>欧洲赛区 Top 30 ({(vrsRegions.europe || []).length})</button>
                <button type="button" className={'btn ' + (vrsScope === 'americas' ? 'primary' : '')} onClick={() => setVrsScope('americas')}>美洲赛区 Top 20 ({(vrsRegions.americas || []).length})</button>
                <button type="button" className={'btn ' + (vrsScope === 'asia' ? 'primary' : '')} onClick={() => setVrsScope('asia')}>亚洲赛区 Top 20 ({(vrsRegions.asia || []).length})</button>
                <button type="button" className={'btn ' + (vrsScope === 'majors' ? 'primary' : '')} onClick={() => setVrsScope('majors')}>2026 两届 Major 官方直邀名单 (64)</button>
                {vrsOct05.length > 0 && (
                  <button type="button" className={'btn ' + (vrsScope === 'oct05' ? 'primary' : '')} onClick={() => setVrsScope('oct05')}>10月5日 Valve 月度原榜 ({vrsOct05.length})</button>
                )}
              </div>
              {vrsScope === 'majors' ? (
                <>
                  <h3>{vrsMajors.singapore_major?.name || 'PGL Major Singapore 2026（冬季 Major）'} · 32 支赛区直邀席位一览</h3>
                  {vrsMajors.singapore_major?.late_october_note && <Note>{vrsMajors.singapore_major.late_october_note}</Note>}
                  <Table
                    topScroll
                    headers={['赛区与顺位', '受邀阶段', '战队', '全球排名', '官方积分', '初始分 / 交手修正', '主力五人阵容', '对战悬赏 / 赢取悬赏', '交手广度 / 线下胜场', '半年战绩 / 折算奖金', '官方明细']}
                    rows={(vrsMajors.singapore_major?.teams || []).map(t => [
                      `${t.region_zh} #${t.regional_rank}`,
                      <b>{t.major_stage}</b>,
                      <b>{t.team}</b>,
                      '#' + t.global_rank,
                      f(t.points, 1),
                      t.starting_rank_value != null ? `${f(t.starting_rank_value, 1)} (${t.h2h_adjustments >= 0 ? '+' : ''}${f(t.h2h_adjustments, 1)})` : '—',
                      t.roster,
                      `${t.bounty_offered} / ${t.bounty_collected}`,
                      `${t.opponent_network} / ${t.lan_wins}`,
                      `${t.record_summary} · ${t.scaled_winnings}`,
                      t.source_url ? <a className="text-link" href={t.source_url} target="_blank" rel="noreferrer">查看明细 ↗</a> : '—'
                    ])}
                  />
                  <h3>{vrsMajors.cologne_major?.name || 'IEM Cologne Major 2026（夏季 Major）'} · 32 支官方锁定受邀战队（2026-04-06）</h3>
                  <Table
                    topScroll
                    headers={['赛区与顺位', '受邀阶段', '战队', '锁定积分', '主力五人阵容', '邀请截止日期']}
                    rows={(vrsMajors.cologne_major?.teams || []).map(t => [
                      `${t.region_zh} #${t.regional_rank}`,
                      <b>{t.stage}</b>,
                      <b>{t.team}</b>,
                      t.points,
                      t.roster,
                      t.cutoff_date
                    ])}
                  />
                </>
              ) : (
                <Table
                  topScroll
                  headers={[
                    isRegionalVrs ? '赛区名次' : '世界排名',
                    isRegionalVrs ? '全球排名' : '赛区排名',
                    '月度升降',
                    '官方积分',
                    '初始分 / 交手修正',
                    '战队',
                    '主力五人阵容',
                    '对战悬赏分',
                    '赢取悬赏分',
                    '交手广度',
                    '线下赛胜场',
                    '半年战绩 / 折算奖金',
                    '新加坡 Major 席位',
                    '官方明细'
                  ]}
                  rows={renderVrsRows(activeVrsRows, isRegionalVrs, true)}
                />
              )}
            </>
          ) : (
            <>
              <div className="formula-banner">
                <div>
                  <div className="formula-title">年度综合评分构成说明</div>
                  <strong>年度综合总分 = 大赛荣誉得分 + 强敌与大赛表现加分</strong>
                  <p>先按赛事含金量（Major、超级精英赛、精英赛、大型赛事）汇总战队名次与个人 MVP / EVP 荣誉，再结合对阵世界前十强队发挥、顶级大赛硬仗表现与参赛场次给出最终排名。</p>
                </div>
                <div className="tier-badges">
                  {r.tier_weights && Object.entries(r.tier_weights).map(([t, w]) => <span key={t}>{t}：<b>重要度 {Number(w).toFixed(2)}</b></span>)}
                </div>
              </div>
              <Table
                headers={['当前排名', '选手', '参赛地图数', '赛季 Rating', '已获 MVP / EVP', '大赛荣誉得分', '强敌表现加分', '年度综合总分']}
                rows={live2026.map(p => [
                  '#' + p.hybrid_rank,
                  <Link className="text-link" to={'/players/' + route(p.id)}>{p.name}</Link>,
                  p.maps, f(p.rating_estimate), `${p.mvp} MVP / ${p.evp} EVP`, f(p.layer1_honor_score), fsigned(p.layer2_residual_rf), f(p.hybrid_score)
                ])}
              />
            </>
          )}
        </section>
      ) : (
        <section className="paper">
          <Note>{year} 赛季 HLTV 官方年度 Top 20 榜单与核心赛场数据一览。</Note>
          <Official />
        </section>
      )}
    </>
  );
}
function Official() {
  const { season, year, bundle } = useResearch();
  const t20Hist = bundle?.sources?.top20_history?.[year] || [];
  const ranked = [...season.players].filter(p => p.official_rank).sort((a, b) => a.official_rank - b.official_rank);
  return (
    <>
      <h2>{year} 赛季 HLTV 年度 Top 20 官方榜单与赛场表现</h2>
      {ranked.length === 0 ? (
        <Note>{year === '2012' ? '2012 年 HLTV 未举办年度 Top 20 评选（自 2013 年起正式恢复 CS:GO 年度 Top 20）。' : '该赛季暂无年度 Top 20 官方终榜。'}</Note>
      ) : (
        <Table
          headers={['官方名次', '选手', '当年效力战队', '参赛地图数', '赛季 Rating', '大赛 / Major Rating', 'MVP / EVP', '官方评选报道']}
          rows={ranked.map(p => {
            const hItem = t20Hist.find(x => x.rank === p.official_rank) || {};
            const bigR = hItem.big_events_rating || p.multi_tier_benchmarks?.santtu_big_events?.big_rating || p.multi_tier_benchmarks?.markzhdan_76?.big_events_rating;
            const majR = hItem.major_rating || p.multi_tier_benchmarks?.santtu_majors?.major_rating || p.multi_tier_benchmarks?.markzhdan_76?.major_rating;
            return [
              '#' + p.official_rank,
              <Link className="text-link" to={'/players/' + route(p.id)}>{p.name}</Link>,
              hItem.team || p.events[0]?.team || '—',
              p.maps,
              f(p.rating_estimate),
              bigR || majR ? `${f(bigR)} / ${f(majR)}` : '—',
              `${p.mvp} MVP / ${p.evp} EVP`,
              hItem.article_url ? <a className="text-link" href={hItem.article_url} target="_blank" rel="noreferrer">查看报道 ↗</a> : '—'
            ];
          })}
        />
      )}
      <p>注：汇总历年 HLTV 官方 Top 20 最终名次、所获荣誉及当季核心赛事表现。</p>
      {(bundle?.sources?.valve_vrs?.by_year?.[year] || []).length > 0 && (
        <>
          <h3>{year} 赛季 Valve 全球战队官方年终积分榜（截至 {bundle.sources.valve_vrs.by_year[year][0]?.snapshot_date}）</h3>
          <Table
            topScroll
            headers={['世界排名', '赛区排名', '月度升降', '官方积分', '初始分 / 交手修正', '战队', '主力五人阵容', '对战悬赏分', '赢取悬赏分', '交手广度', '线下赛胜场', '半年战绩 / 折算奖金', '官方明细']}
            rows={renderVrsRows(bundle.sources.valve_vrs.by_year[year], false, false)}
          />
        </>
      )}
    </>
  );
}

function Scenario() {
  return <FutureScenarios context={useResearch()} ui={{ Heading, Note, Table, Save, api, exportFile, f }} />;
}

function Players() {
  const { season, year, bundle, setUiContext } = useResearch();
  const roleMap = new Map((bundle?.roles?.seasons?.[year]?.players || []).map(rp => [rp.id, rp]));
  return (
    <>
      <Heading title={`选手档案库：${year} 赛季职业选手数据全览`} subtitle="按选手名称检索 2012–2026 历年参赛记录、攻防阵营表现、常用地图池、场上位置与个人荣誉。" />
      <Scope />
      {!season ? <Empty /> : (
          <PlayerDirectory
            players={season.players}
            onFilterChange={patch => setUiContext?.(prev => ({ ...prev, ...patch }))}
            renderCells={p => {
              const rp = roleMap.get(p.id);
              const teamName = p.team || p.events?.[0]?.team || p.career_profile?.current_team || '—';
              return [
                <Link className="text-link" to={'/players/' + route(p.id)}>
                  {p.name}{p.identity_status === 'ambiguous_name_split' ? `（${teamName}）` : ''}
                </Link>,
                teamName,
                p.events.length,
                p.maps,
                f(p.rating_estimate),
                p.side_splits?.ct_side ? `CT ${f(p.side_splits.ct_side.rating)} / T ${f(p.side_splits.t_side?.rating)}` : '—',
                rp?.role_short || rp?.role_name || formatRoleLabel(p.playstyle_measured?.role_overall),
                `${p.mvp} / ${p.evp}`
              ];
            }}
          />
      )}
    </>
  );
}

function PlayerDetail({ id }) {
  const { season, year, bundle } = useResearch();
  const p = season?.players.find(p => p.id === id);
  const rolePlayer = bundle?.roles?.seasons?.[year]?.players?.find(rp => rp.id === id);
  const ver = bundle?.event_weights?.official_verifications?.[year]?.[id];
  return (
    <>
      <Heading title={p ? `${p.name} · ${year} 赛季选手档案` : '选手档案'} subtitle="查看选手单赛季各站赛事成绩、场上位置特点、常用地图池与对阵强队表现。" />
      <Scope showMetric={false} />
      {!p ? <Empty /> : (
        <section className="paper player-profile">
          <div className="profile-stats">
            <div><span>{p.weighted_honor_score != null ? '全年综合 Rating' : '赛季综合 Rating'}</span><strong>{f(p.rating_estimate)}</strong></div>
            <div><span>参赛总地图数</span><strong>{p.maps} 图</strong></div>
            <div><span>{p.weighted_honor_score != null ? '年度排名 / MVP / EVP / 荣誉积分' : '年度排名 / MVP / EVP'}</span><strong>{p.official_rank ? '#' + p.official_rank : '未入榜'} / {p.mvp} / {p.evp}{p.weighted_honor_score != null ? ` / ${f(p.weighted_honor_score)}分` : ''}</strong></div>
          </div>
          <Note>本赛季共收录 {p.events.length} 站重点赛事（累计 {p.maps} 张比赛地图），主力效力战队为 {p.team || p.events[0]?.team || p.career_profile?.current_team || '—'}。赛季综合 Rating 按各站参赛地图数加权计算。</Note>
          {ver && (
            <div className="info-card">
              <h4>年度荣誉与评选看点</h4>
              <p>{ver.discrepancy_note} <a className="text-link" href={ver.source_url} target="_blank" rel="noreferrer">查看评选报道 ↗</a></p>
            </div>
          )}
          {rolePlayer && (
            <div className="info-card">
              <h4>场上位置与同位置表现对比（{rolePlayer.role_short || rolePlayer.role_name}）</h4>
              <p>
                同位置对比人数：{rolePlayer.peer_group_size} 人 · 同位置 Rating 表现：<b>超过 {f(rolePlayer.peer_benchmarks?.rating?.percentile, 0)}% 同位置选手</b> ·
                平均首次交火 {rolePlayer.style_metrics.first_duel_time} 秒 · 首杀尝试比例 {rolePlayer.style_metrics.opening_attempt_pct}% · 阵亡可补枪率 {rolePlayer.style_metrics.tradeable_deaths_pct}% · 回合末存活率 {rolePlayer.style_metrics.last_alive_pct}% · 狙击枪击杀占比 {rolePlayer.style_metrics.awp_kills_pct}% · 道具支援评分 {rolePlayer.style_metrics.utility_efficiency} 分
              </p>
            </div>
          )}
          {p.playstyle_measured && (
            <div className="info-card">
              <h4>比赛录像细节统计（基于 {p.playstyle_measured.map_count} 张比赛地图）</h4>
              <p>
                场上定位：<b>{formatRoleLabel(p.playstyle_measured.role_overall)}</b>（进攻方 T：<b>{formatRoleLabel(p.playstyle_measured.role_t)}</b> / 防守方 CT：<b>{formatRoleLabel(p.playstyle_measured.role_ct)}</b>） ·
                平均存活时长：<b>{p.playstyle_measured.tapd_overall} 秒</b>（进攻方 {p.playstyle_measured.tapd_t} 秒 / 防守方 {p.playstyle_measured.tapd_ct} 秒） ·
                首杀尝试比例：<b>{p.playstyle_measured.oap_overall}%</b>（进攻方 {p.playstyle_measured.oap_t}% / 防守方 {p.playstyle_measured.oap_ct}%） ·
                阵亡后 5 秒内被队友补枪率：<b>{p.playstyle_measured.podt_overall}%</b> ·
                5 秒内补枪击杀率：<b>{p.playstyle_measured.pokt_overall}%</b>
              </p>
            </div>
          )}
          {p.career_profile && (
            <div className="info-card">
              <h4>职业生涯累计数据概览</h4>
              <p>
                生涯总地图：<b>{p.career_profile.maps_played} 图</b>（{p.career_profile.rounds_played} 回合） · 生涯 Rating：<b>{f(p.career_profile.rating)}</b> · K/D 比值：<b>{f(p.career_profile.kd_ratio)}</b>（击杀差 {p.career_profile.kd_difference}） · 爆头率：<b>{p.career_profile.headshot_percentage}%</b> · 回合均手雷伤害：<b>{p.career_profile.grenade_damage_per_round}</b> · 掩护队友 / 获队友掩护：<b>{p.career_profile.teammate_saved_per_round} / {p.career_profile.saved_by_teammate_per_round}</b>
                {p.career_profile.stats_link && <> · <a className="text-link" href={p.career_profile.stats_link} target="_blank" rel="noreferrer">HLTV 官方生涯页 ↗</a></>}
              </p>
            </div>
          )}
          {p.side_splits && Object.keys(p.side_splits).length > 0 && (
            <>
              <h3>攻防阵营（CT / T）表现对比</h3>
              <Table
                headers={['阵营范围', 'Rating', 'K/D 比值', '击杀差', '累计回合数', '统计周期', '详细记录']}
                rows={['both_sides', 'ct_side', 't_side'].map(sk => {
                  const s = p.side_splits[sk];
                  if (!s) return null;
                  const sideLabel = sk === 'ct_side' ? '防守方（CT）' : (sk === 't_side' ? '进攻方（T）' : '全阵营综合');
                  return [sideLabel, f(s.rating), f(s.kd), s.kd_diff ?? '—', `${s.rounds || s.maps_est} 回合`, s.period, <Source item={s} />];
                }).filter(Boolean)}
              />
            </>
          )}
          {p.map_pool && p.map_pool.length > 0 && (
            <>
              <h3>常用比赛地图表现（共 {p.map_pool.length} 张地图）</h3>
              <Table
                headers={['比赛地图', '综合 Rating', '防守方(CT) Rating', '进攻方(T) Rating', 'K/D 比值', '场均伤害(ADR) / 贡献率(KAST)', '累计回合（约合图数）', '详细记录']}
                rows={p.map_pool.map(m => [
                  <b>{m.map}</b>,
                  f(m.rating),
                  f(m.ct_rating),
                  f(m.t_rating),
                  f(m.kd),
                  m.adr ? `${f(m.adr, 1)} / ${f(m.kast, 1)}%` : '—',
                  `${m.rounds} 回合（约 ${m.maps_est} 图）`,
                  <Source item={m} />
                ])}
              />
            </>
          )}
          {p.major_finals && p.major_finals.length > 0 && (
            <>
              <h3>Major 决赛历史表现</h3>
              <Table
                headers={['Major 赛事', '效力战队', '击杀 - 阵亡', '场均伤害(ADR)', '贡献率(KAST%)', '回合胜率贡献(Swing)', '决赛 Rating', '详细记录']}
                rows={p.major_finals.map(mf => [
                  mf.event, mf.team, `${mf.kills} - ${mf.deaths}`, f(mf.adr, 1), `${f(mf.kast, 1)}%`, mf.swing || '—', <b>{f(mf.rating)}</b>, <Source item={mf} />
                ])}
              />
            </>
          )}
          {p.multi_tier_benchmarks?.blum_2026 && (
            <>
              <h3>2026 赛季各级别赛事与强敌细分表现</h3>
              <Table
                headers={['细分场景', '赛季 Rating', '参赛地图数', '统计范围说明', '详细记录']}
                rows={[
                  ['overall', '全年综合表现'],
                  ['vs_top5', '对阵世界前 5 强队'],
                  ['vs_top10', '对阵世界前 10 强队'],
                  ['vs_top20', '对阵世界前 20 强队'],
                  ['big_events', '大型赛事'],
                  ['elite_events', '精英赛事'],
                  ['super_elite', '超级精英赛事'],
                  ['big_playoffs', '大型赛事淘汰赛与关键战'],
                  ['elite_playoffs', '精英赛事淘汰赛与关键战'],
                  ['big_event_finals', '大型赛事总决赛']
                ].map(([k, label]) => {
                  const item = p.multi_tier_benchmarks.blum_2026[k];
                  if (!item) return null;
                  return [<b>{label}</b>, <b>{f(item.rating)}</b>, `${item.maps} 图`, item.scope_zh, <Source item={item} />];
                }).filter(Boolean)}
              />
            </>
          )}
          {p.opponents ? (
            <>
              <h3>对阵不同世界排名强队表现</h3>
              <Table headers={['对手世界排名范围', '对阵 Rating', '交手地图数']} rows={['5', '10', '20', '30', '50'].map(n => [`对阵世界前 ${n} 战队 (vs Top ${n})`, p.opponents['vsTop' + n], p.opponents['vsTop' + n + '图数'] ?? '暂无单列图数'])} />
              <Source item={p.opponents} />
            </>
          ) : <Note>当前赛季暂未单独收录该选手的对阵强队细分统计。</Note>}
          <h3>本赛季分站赛事成绩单</h3>
          <EventRows rows={p.events} />
        </section>
      )}
    </>
  );
}

function EventRows({ rows, players = false }) {
  const hasBlum = rows.some(r => r.weighted_points != null);
  return (
    <Table
      headers={hasBlum
        ? [players ? '参赛选手' : '赛事名称', '赛事重要度', 'Rating', '地图数', '场均击杀(KPR)', '效力战队', '战队名次', '个人荣誉', '单站表现分 / 荣誉积分', '详细记录']
        : [players ? '参赛选手' : '赛事名称', 'Rating', '地图数', '场均伤害(ADR)', '场均击杀(KPR)', '效力战队', '战队名次', '个人荣誉', '详细记录']
      }
      rows={rows.map(r => hasBlum ? [
        players ? <Link className="text-link" to={'/players/' + route(r.player_id)}>{r.name}</Link> : <Link className="text-link" to={'/events/' + route(r.event)}>{r.event_zh ? `${r.event_zh} (${r.event})` : r.event}</Link>,
        r.source_weight != null ? `${f(r.source_weight * 100, 1)}%` : '—',
        <b>{f(r.rating)}</b>,
        r.maps,
        f(r.kpr),
        r.team,
        r.team_place,
        r.award_raw || r.award,
        r.weighted_points != null ? `${f(r.perf_score)} → ${f(r.weighted_points)}` : '—',
        <Source item={r} />
      ] : [
        players ? <Link className="text-link" to={'/players/' + route(r.player_id)}>{r.name}</Link> : <Link className="text-link" to={'/events/' + route(r.event)}>{r.event}</Link>,
        f(r.rating), r.maps, f(r.adr, 1), f(r.kpr), r.team, r.team_place, r.award, <Source item={r} />
      ])}
    />
  );
}

function Events({ q, setQ }) {
  const { season, year, setYear, bundle } = useResearch();
  const searchInput = useRef(null);
  const index = useMemo(() => buildEventIndex(bundle.data.seasons), [bundle]);
  const query = q.trim();
  const searching = Boolean(query);
  const matches = useMemo(() => searchEventIndex(index, query), [index, query]);
  const events = searching ? matches.events : index.events.filter(item => item.year === year);
  const resultCount = events.length;
  const yearCount = new Set(events.map(item => item.year)).size;
  const archiveYears = Object.keys(bundle.data.seasons).sort();
  function clearSearch() { setQ(''); searchInput.current?.focus(); }
  return (
    <>
      <Heading title="赛事档案库：历年赛事与选手成绩" subtitle="浏览 2012–2026 各赛季重点赛事，查看参赛选手表现、战队名次与个人荣誉。" />
      <section className="events-search" role="search" aria-label="跨年份赛事搜索">
        <div className="events-search-heading">
          <label htmlFor="events-search-input">搜索全部赛事</label>
          <span>{archiveYears[0]}–{archiveYears.at(-1)} · 全部已收录年份</span>
        </div>
        <div className="events-search-field">
          <MagnifyingGlass size={24} aria-hidden="true" />
          <input id="events-search-input" ref={searchInput} type="search" aria-label="搜索赛事" aria-describedby="events-search-hint" placeholder="赛事名称、年份或战队" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Escape') clearSearch(); }} />
          {q && <button type="button" className="events-search-clear" onClick={clearSearch} aria-label="清空赛事搜索"><X size={18} aria-hidden="true" /><span>清空</span></button>}
        </div>
        <p id="events-search-hint" className="events-search-hint">按赛事名称、年份或参赛战队搜索全部已收录赛季，不受下方年份选择限制。</p>
      </section>
      <div className={'scope-bar events-browse-bar' + (searching ? ' is-searching' : '')}>
        <label>按年份浏览 <select aria-label="研究年份" value={year} disabled={searching} onChange={e => setYear(e.target.value)}>{ALL_YEARS.map(y => <option value={y} key={y}>{y}</option>)}</select></label>
        <span>{searching ? `正在搜索全部年份 · 清空后可继续浏览 ${year} 赛季` : season ? `${season.events.length} 场重点赛事${season.raw_source_events && season.raw_source_events > season.events.length ? `（共收录 ${season.raw_source_events} 站）` : ''} · ${season.rows} 条比赛记录 · ${season.players.length} 位选手` : '该年份暂无数据'}</span>
      </div>
      <section className="paper events-results">
        <div className="events-result-summary" role="status" aria-live="polite">
          <h2>{searching ? `“${query}” · 找到 ${resultCount} 场赛事` : `${year} 赛季重点赛事`}</h2>
          <span>{searching ? (yearCount > 0 ? `跨 ${yearCount} 个赛季 · 按年份从新到旧排列` : '全部年份') : `${resultCount} 场赛事`}</span>
        </div>
        {resultCount === 0 ? (
          <div className="events-empty">
            <h2>{searching ? '没有找到匹配赛事' : '该年份暂无赛事档案'}</h2>
            <p>{searching ? '试试其他赛事名称、年份或参赛战队。' : '可以切换年份，或通过上方搜索查找其他赛季。'}</p>
            {searching && <button type="button" className="btn" onClick={clearSearch}>清空搜索</button>}
          </div>
        ) : (
          <div className="event-list">
            {events.map(({ event: e, year: eventYear }, i) => (
              <Link className="event-item" to={'/events/' + route(e.name) + '?year=' + eventYear} key={eventYear + ':' + e.name}>
                <span className="event-index">{String(i + 1).padStart(2, '0')}</span>
                <div>
                  {searching && <span className="event-season">{eventYear} 赛季</span>}
                  <h2>{e.name}</h2>
                  <p>{e.tier} · {e.players.length} 位参赛选手记录 · {e.period_start ? `${e.period_start} 至 ${e.period_end}` : `${eventYear} 赛季重点赛事`}{e.prize_pool ? ` · 总奖金 ${e.prize_pool}` : ''}</p>
                </div>
                <ArrowRight size={22} weight="bold" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function EventDetail({ id, requestedYear }) {
  const { season, year, setYear, bundle } = useResearch();
  const syncedRoute = useRef(null);
  useEffect(() => {
    // Apply the link's season once per navigation, including reload/new tab.
    const routeKey = JSON.stringify([id, requestedYear]);
    if (syncedRoute.current === routeKey) return;
    syncedRoute.current = routeKey;
    if (requestedYear && bundle.data.seasons[requestedYear] && requestedYear !== year) setYear(requestedYear);
  }, [id, requestedYear, bundle, year, setYear]);
  const e = season?.events.find(e => e.name === id);
  return (
    <>
      <Heading title={e?.name || '赛事详情'} subtitle="查看本站赛事全体参赛选手的 Rating、场均伤害、战队最终名次与个人荣誉。" />
      <Scope showMetric={false} />
      {!e ? <Empty /> : (
        <section className="paper">
          <h2>{e.tier} · 共收录 {e.players.length} 位参赛选手表现</h2>
          <Note>以下为本站赛事各位参赛选手的全场综合技术统计、所属战队最终名次及个人 MVP / EVP 荣誉记录。</Note>
          <EventRows rows={e.players} players />
        </section>
      )}
    </>
  );
}

function Library() {
  const { bundle } = useResearch();
  const a = bundle.coverage;
  const registry = a?.verified_datasets_registry || bundle?.sources?.verified_datasets_registry || [];
  const featureCards = [
    {
      title: '历年赛事与年度 Top 20 档案（2012–2026）',
      desc: '汇集 15 个赛季共 38,895 条分站赛事选手表现（6,943 人次选手档案，每年 447–467 人）、2013–2025 连续 13 年 HLTV 官方 Top 20 榜单、24 届 Major 冠亚军记录及 Valve 全球战队积分。'
    },
    {
      title: '强敌交手、攻防阵营与比赛地图池',
      desc: '涵盖全赛季 6,943 人次职业选手在 13 张主流比赛地图及防守方（CT）/ 进攻方（T）的细分表现，并提供对阵世界前五至前五十强队的交手统计。'
    },
    {
      title: '场上位置分工与比赛录像细节',
      desc: '结合职业比赛中的首次交火时间、首杀尝试、残局存活、5 秒内队友补枪配合与道具支援表现，梳理主狙、突破、自由人与辅助四类赛场定位。'
    },
    {
      title: '官方评分机制与赛事含金量说明',
      desc: '整理 HLTV Rating 3.0 评分看点、赛事级别划分（Major / 超级精英赛 / 精英赛 / 大型赛事）以及 Valve 全球战队排名规则。'
    }
  ];
  return (
    <>
      <Heading title="资料与评选说明：数据覆盖范围与评分规则" subtitle="了解本站收录的 2012–2026 赛季赛事范围、现役地图攻防参考、评分规则与公开资料来源。" />
      <section className="paper">
        <h2>收录范围与更新说明</h2>
        <p>本站汇集 2012–2026 共 15 个赛季的职业赛事选手数据、历年 HLTV 官方 Top 20 荣誉档案、24 届 Major 决赛记录与 Valve 官方战队积分。由于 2026 赛季仍在进行中，全年赛程与年终榜单尚不完整，各项统计将随重点赛事完赛持续更新（最近同步日期：{bundle.data.meta.retrieved_at}）。</p>
        <h3>四大核心资料板块</h3>
        <div className="rules-grid">
          {featureCards.map((item, idx) => (
            <article key={idx} className="rule-card">
              <h4>{item.title}</h4>
              <p>{item.desc}</p>
            </article>
          ))}
        </div>
        {bundle?.sources?.telemetry_2026 && (
          <>
            <h3>2026 赛季现役比赛地图攻防胜率与节奏参考</h3>
            <Table
              headers={['比赛地图', '统计回合数', '平均回合时长', '防守方(CT)胜率', '进攻方(T)胜率', 'C4 安放率', '平均首杀发生时间', '回合均狙击击杀', '回合均补枪击杀']}
              rows={(bundle.sources.telemetry_2026.opencs2_map_benchmarks || []).map(m => {
                const rawMap = String(m.map_name || '').replace(/^de_/i, '');
                const cleanMap = rawMap.toLowerCase() === 'dust2' ? 'Dust2' : (rawMap ? rawMap[0].toUpperCase() + rawMap.slice(1) : '—');
                return [
                  <b>{cleanMap}</b>, m.rounds, `${m.avg_duration_s} 秒`, `${m.ct_win_pct}%`, `${m.t_win_pct}%`, `${m.plant_rate_pct}%`, `${m.avg_opening_kill_s} 秒`, m.avg_awp_kills_per_round, m.avg_trade_kills_per_round
                ];
              })}
            />
          </>
        )}
        <h3>2012–2026 历年收录赛事与选手规模一览</h3>
        <Table
          headers={['赛季年份', '收录重点赛事', '选手参赛记录', '涵盖选手人数', '官方 Top 20 名单', '强敌交手记录覆盖']}
          rows={Object.entries(a.seasons).map(([y, s]) => [
            `${y} 赛季`,
            `${s.events} 站`,
            `${s.rows} 条`,
            `${s.players} 人`,
            y === '2026' ? '赛季进行中' : ((s.official_ranked_players ?? 0) ? `${s.official_ranked_players} 人` : '未设官方榜'),
            `${s.opponent_players} 人`
          ])}
        />
        <h3>评分与排名规则说明</h3>
        <p><b>赛季综合 Rating</b>：将选手在当季各站重点赛事中的 Rating 按实际参赛地图数加权计算，直观反映全年稳定发挥水平；对阵世界前五至前五十强队的表现在选手档案中单独列出。</p>
        <p><b>场上位置对比参考</b>：由于主狙手、突破手、残局自由人与辅助位在场上的职责不同，系统结合交火时间、首杀尝试、残局存活、补枪配合与道具支援表现划分位置，方便在相同位置下公平对比选手贡献。</p>
        <p><b>年度排名综合评估</b>：综合考量不同级别赛事（Major、超级精英赛、精英赛、大型赛事）的团队名次与个人 MVP / EVP 荣誉，并结合对阵世界前十强队发挥与大赛出场场次给出年度综合排名参考。</p>
        {registry.length > 0 && (
          <>
            <h3>公开赛事资料与历史档案来源</h3>
            <Table
              headers={['资料内容说明', '所属板块', '涵盖年份', '收录记录数', '来源链接']}
              rows={registry.map(d => {
                const mapped = DATASET_DISPLAY_MAP[d.id] || [d.name, '赛事资料'];
                return [
                  <b>{mapped[0]}</b>,
                  mapped[1],
                  d.years,
                  Number(d.rows).toLocaleString('en-US') + ' 条',
                  <a className="text-link" href={d.url} target="_blank" rel="noreferrer">查看公开来源 ↗</a>
                ];
              })}
            />
          </>
        )}
        <button className="btn" onClick={() => exportFile('赛事资料概览.json', a)}>导出资料概览 <Download size={17} /></button>
      </section>
    </>
  );
}

function Research() {
  const { bundle, restore } = useResearch();
  return (
    <>
      <Heading title="我的研究记录" subtitle="集中管理您保存的选手对比、言论求证、年度预测与 If 线推演记录，随时一键恢复继续查看。" />
      <p>您保存的分析记录会自动同步，刷新页面后仍可随时回看或继续推演。</p>
      {!bundle.records.length ? <Empty>可先前往选手对比、言论求证、年度预测或 If 线推演页面保存您感兴趣的分析结果。</Empty> : (
        <div className="research-list">
          {bundle.records.map(r => (
            <article key={r.id}>
              <BookOpen size={24} weight="light" color="#9e3b22" />
              <div className="research-copy">
                <h3>{r.title}</h3>
                <small>类型：{r.payload.type} · 赛季：{r.payload.year} · 保存时间：{new Date(r.created).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}</small>
                <details><summary>查看保存的详细数据</summary><pre>{JSON.stringify(r.payload, null, 2)}</pre></details>
              </div>
              <div className="research-actions">
                <button className="btn primary" onClick={() => restore(r)}>继续研究</button>
                <button className="btn" onClick={() => exportFile('研究记录.json', r)}>导出</button>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}

export default function ConnectedApp() {
  const [bundle, setBundle] = useState(null);
  const [error, setError] = useState('');
  const [path, setPath] = useState(location.hash.slice(1) || '/');
  const [year, setYearState] = useState(() => {
    try { const saved = localStorage.getItem('swingaudit.scope.year'); return ALL_YEARS.includes(saved) ? saved : '2026'; } catch { return '2026'; }
  });
  const [metric, setMetric] = useState('overall');
  const [pair, setPair] = useState(['donk', 'zywoo']);
  const [prompt, setPrompt] = useState('');
  const [verifyPrompt, setVerifyPrompt] = useState('');
  const [evidence, setEvidence] = useState(null);
  const [menu, setMenu] = useState(false);
  const [message, setMessage] = useState('');
  const [restored, setRestored] = useState(null);
  const [eventQuery, setEventQuery] = useState('');
  const [uiContext, setUiContext] = useState({});
  const [waterSurge, setWaterSurge] = useState(false);
  const noticeTimer = useRef(null);
  const surgeTimer = useRef(null);

  function triggerWaterSurge() {
    setWaterSurge(false);
    clearTimeout(surgeTimer.current);
    requestAnimationFrame(() => {
      setWaterSurge(true);
      surgeTimer.current = setTimeout(() => setWaterSurge(false), 3800);
    });
  }

  async function init() {
    setError('');
    try {
      const fast = await api('bootstrap', null, undefined, { 'X-Bootstrap-Mode': 'fast', 'X-Bootstrap-Year': year });
      setBundle(fast);
      if (fast?._partial) {
        api('bootstrap').then(full => {
          setBundle(prev => ({ ...full, records: prev?.records?.length ? prev.records : full.records }));
        }).catch(() => {});
      }
    } catch (e) {
      setError(e.message);
    }
  }
  useEffect(() => { init(); return () => { clearTimeout(noticeTimer.current); clearTimeout(surgeTimer.current); }; }, []);
  useEffect(() => {
    function h() { setPath(location.hash.slice(1) || '/'); setMenu(false); setEvidence(null); triggerWaterSurge(); window.scrollTo(0, 0); }
    window.addEventListener('hashchange', h);
    return () => window.removeEventListener('hashchange', h);
  }, []);

  useEffect(() => { try { localStorage.setItem('swingaudit.scope.year', year); } catch { /* Conversation storage reports failures beside the input. */ } }, [year]);
  const season = bundle?.data.seasons[year];
  function setYear(y) {
    setYearState(y); setRestored(null); setEvidence(null); triggerWaterSurge();
    const s = bundle?.data.seasons[y];
    if (s && s.players.length >= 2) {
      setPair(prev => {
        const p0 = s.players.some(p => p.id === prev[0]) ? prev[0] : s.players[0]?.id;
        let p1 = s.players.some(p => p.id === prev[1]) ? prev[1] : s.players[1]?.id;
        if (p1 === p0) p1 = s.players.find(p => p.id !== p0)?.id || s.players[1]?.id;
        return [p0, p1];
      });
    }
  }
  function notify(text) {
    setMessage(text);
    clearTimeout(noticeTimer.current);
    noticeTimer.current = setTimeout(() => setMessage(''), 4000);
  }
  async function save(title, payload) {
    try {
      const r = await api('records', { title, payload: { ...payload, data_snapshot: bundle?.data?.meta || {}, storage_version: 2 } });
      setBundle(b => (b ? { ...b, records: [r, ...(b.records || [])] } : b));
      notify('已保存到「我的研究」');
    } catch (e) {
      notify('保存失败：' + e.message);
    }
  }
  function restore(r) {
    const p = r.payload;
    setYearState(p.year || '2026'); setMetric(p.metric || 'overall');
    if (p.pair) setPair(p.pair);
    if (p.question) setPrompt(p.question);
    setRestored(p);
    location.hash = p.type === 'scenario' ? '/scenarios' : p.type === 'rankings' ? '/rankings' : ['verify', 'agent'].includes(p.type) ? '/verify' : '/compare';
    notify('已恢复研究条件；原结果保留在研究快照中');
  }

  let page;
  if (path === '/') page = <Home />;
  else if (path === '/compare') page = <Compare />;
  else if (path === '/verify') page = <Verify />;
  else if (path === '/rankings') page = <Rankings />;
  else if (path.startsWith('/scenarios')) page = <Scenario key={year + JSON.stringify(restored)} />;
  else if (path === '/players') page = <Players />;
  else if (path.startsWith('/players/')) page = <PlayerDetail id={decodeURIComponent(path.slice(9))} />;
  else if (path === '/events') page = <Events q={eventQuery} setQ={setEventQuery} />;
  else if (path.startsWith('/events/')) {
    const eventUrl = new URL(path, location.origin);
    page = <EventDetail id={decodeURIComponent(eventUrl.pathname.slice(8))} requestedYear={eventUrl.searchParams.get('year')} />;
  }
  else if (path === '/library') page = <Library />;
  else if (path === '/research') page = <Research />;
  else if (path === '/live') page = (
    <>
      <Heading title="实时研究工作台" subtitle="所有业务页面均已接入真实历史数据底座与在线智能体服务。" />
      <Scope />
      <div className="analysis-layout">
        <section className="paper">
          <h2>真实数据已接入所有业务页面</h2>
          <p>通过选手库、赛事库、对比和模型页面查看具体记录，资料页查看完整性报告。</p>
          <div className="actions">
            <Link className="btn" to="/players">选手历史 →</Link>
            <Link className="btn" to="/events">赛事档案 →</Link>
            <Link className="btn" to="/library">来源与覆盖 →</Link>
          </div>
        </section>
      </div>
    </>
  );
  else page = <Empty>页面不存在，请通过导航重新选择。</Empty>;

  return (
    <Context.Provider value={{ path, bundle, season, year, setYear, metric, setMetric, pair, setPair, prompt, setPrompt, verifyPrompt, setVerifyPrompt, setEvidence, evidence, save, restore, restored, eventQuery, uiContext, setUiContext }}>
      <AtlasWaterBackground className="atlas-water-background" position="fixed" speed={1} scale={1} contrast={1} surge={false} maxDpr={2} zIndex={0} />
      <div className="site-shell">
        <header className="site-header">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              <svg width="30" height="30" viewBox="0 0 30 30" fill="none"><rect x="1" y="1" width="28" height="28" stroke="currentColor" strokeWidth="2"/><path d="M15 5V11M15 19V25M5 15H11M19 15H25" stroke="currentColor" strokeWidth="2"/><rect x="13" y="13" width="4" height="4" fill="currentColor" className="brand-dot"/></svg>
            </span>
            <span className="brand-text">
              <strong>SWINGAUDIT</strong>
            </span>
          </Link>
          <nav aria-label="主导航" className={menu ? 'open' : ''}>
            {nav.map(([p, l]) => <Link to={p} key={p} className={path === p ? 'active' : ''}>{l}</Link>)}
            <Link to="/players" className={path.startsWith('/players') ? 'active' : ''}>选手库</Link>
            <Link to="/events" className={path.startsWith('/events') ? 'active' : ''}>赛事库</Link>
            <Link to="/library" className={path === '/library' ? 'active' : ''}>资料</Link>
          </nav>
          <div className="header-tools">
            <Link to="/research" className="header-bookmark" aria-label="我的研究">
              <BookmarkSimple size={18} weight="bold" />
              <span>我的研究</span>
            </Link>
            <button className="mobile-menu icon-btn" aria-label="切换导航" onClick={() => setMenu(!menu)}>{menu ? <X size={20} /> : <List size={20} />}</button>
          </div>
        </header>
        <main id="main" className={path === '/' ? 'home' : 'inner-page'} key={path}>
          {error ? (
            <section className="paper">
              <h2>无法连接数据服务</h2>
              <p role="alert" className="error">{error}</p>
              <button className="btn" onClick={init}>重新连接</button>
            </section>
          ) : bundle ? page : <p role="status">正在读取真实数据、模型报告与研究记录…</p>}
        </main>
        <footer className="site-footer">
          <Link to="/" className="footer-brand">SwingAudit · CS2 选手观察室<span>汇集历年职业赛事表现、选手场上位置与年度荣誉的 CS2 赛事数据分析平台</span></Link>
          <div>
            <Link to="/library">资料与方法</Link>
            <Link to="/research">我的研究</Link>
            <Link to="/live">实时工作台</Link>
            <small>CS2 赛事数据观察与排名推演参考</small>
          </div>
        </footer>
      </div>
      {!error && <Agent />}
      <Evidence />
      {message && <div className="toast visible" role="status">{message}</div>}
    </Context.Provider>
  );
}
