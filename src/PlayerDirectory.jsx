import React, { useEffect, useRef, useState } from 'react';
import { MagnifyingGlass, X } from '@phosphor-icons/react';
import './players.css';

const initials = ['#', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
const collator = new Intl.Collator('en', { sensitivity: 'base', numeric: true });
const normalizedName = name => String(name || '').trim().normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
const initialOf = name => {
  const first = normalizedName(name).charAt(0).toUpperCase();
  return /^[A-Z]$/.test(first) ? first : '#';
};
const headers = ['选手', '主力战队', '参赛站数', '总地图数', '赛季 Rating', '防守(CT) / 进攻(T)', '场上位置', 'MVP / EVP'];

export default function PlayerDirectory({ players, renderCells, onFilterChange }) {
  const [query, setQuery] = useState('');
  const [direction, setDirection] = useState('asc');
  const [located, setLocated] = useState('');
  const viewport = useRef(null);
  const searchInput = useRef(null);
  const search = normalizedName(query).toLowerCase();
  const visiblePlayers = players.filter(p => normalizedName(p.name).toLowerCase().includes(search)).sort((a, b) => {
    const groupOrder = initials.indexOf(initialOf(a.name)) - initials.indexOf(initialOf(b.name));
    const order = groupOrder || collator.compare(normalizedName(a.name), normalizedName(b.name)) || collator.compare(a.id, b.id);
    return direction === 'asc' ? order : -order;
  });
  const counts = new Map();
  visiblePlayers.forEach(p => counts.set(initialOf(p.name), (counts.get(initialOf(p.name)) || 0) + 1));

  useEffect(() => {
    setLocated('');
    viewport.current?.scrollTo({ top: 0, behavior: 'instant' });
  }, [query, direction, players]);
  useEffect(() => {
    onFilterChange?.({ playerSearch: query, playerInitial: located, visiblePlayerCount: visiblePlayers.length });
  }, [query, located, visiblePlayers.length]);

  const locate = initial => {
    const wrap = viewport.current;
    const row = wrap?.querySelector(`tr[data-initial="${initial}"]`);
    if (!row) return;
    const header = wrap.querySelector('thead');
    const top = wrap.scrollTop + row.getBoundingClientRect().top - wrap.getBoundingClientRect().top - header.getBoundingClientRect().height - wrap.clientTop;
    wrap.scrollTo({ top, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    setLocated(initial);
  };

  const clearSearch = () => { setQuery(''); searchInput.current?.focus(); };

  return (
    <section className="paper player-directory">
      <div className="player-directory-tools">
        <div className="player-search">
          <MagnifyingGlass size={19} aria-hidden="true" />
          <input ref={searchInput} type="search" aria-label="搜索选手" placeholder="搜索选手名称，如 donk、ZywOo、s1mple" value={query} onChange={e => setQuery(e.target.value)} />
          {query && <button type="button" className="player-search-clear" aria-label="清空搜索" onClick={clearSearch}><X size={17} /></button>}
        </div>
        <div className="player-sort" role="group" aria-label="选手名称排序">
          <button type="button" aria-pressed={direction === 'asc'} onClick={() => setDirection('asc')}>正序 <span>A–Z</span></button>
          <button type="button" aria-pressed={direction === 'desc'} onClick={() => setDirection('desc')}>倒序 <span>Z–A</span></button>
        </div>
      </div>
      <nav className="player-alphabet" aria-label="按首字母定位选手">
        <span className="player-alphabet-label">首字母定位</span>
        <div className="player-alphabet-keys">
          {initials.map(initial => <button key={initial} type="button" disabled={!counts.has(initial)} aria-current={located === initial ? 'location' : undefined}
            aria-label={`定位${initial === '#' ? '数字或符号' : initial}开头的选手`}
            title={`${initial === '#' ? '数字 / 符号' : initial} · ${counts.get(initial) || 0} 位选手`}
            onClick={() => locate(initial)}>{initial}</button>)}
        </div>
      </nav>
      <div className="player-directory-status" role="status" aria-live="polite" aria-atomic="true">
        <span>{search ? `找到 ${visiblePlayers.length} / ${players.length} 位选手` : `共 ${players.length} 位选手`}<span className="player-count-divider">·</span>按名称{direction === 'asc' ? '正序' : '倒序'}</span>
        <span>{located ? `已定位 ${located === '#' ? '数字 / 符号' : located} · ${counts.get(located) || 0} 位` : '点击字母，跳转至对应选手'}</span>
      </div>
      {visiblePlayers.length ? (
        <div className="table-wrap player-directory-table" ref={viewport} tabIndex={0} role="region" aria-label="选手档案列表">
          <table>
            <thead><tr>{headers.map((h, i) => <th key={h} scope="col" aria-sort={i === 0 ? (direction === 'asc' ? 'ascending' : 'descending') : undefined}>{h}{i === 0 && <span className="player-sort-arrow" aria-hidden="true">{direction === 'asc' ? '↑' : '↓'}</span>}</th>)}</tr></thead>
            <tbody>{visiblePlayers.map(p => <tr key={p.id} data-initial={initialOf(p.name)} className={located === initialOf(p.name) ? 'player-row-located' : undefined}>{renderCells(p).map((cell, i) => <td key={i}>{cell ?? '—'}</td>)}</tr>)}</tbody>
          </table>
        </div>
      ) : (
        <div className="empty player-search-empty">
          <h3>没有找到匹配的选手</h3>
          <p>试试其他名称，或清空搜索查看本赛季全部选手。</p>
          <button type="button" className="text-link" onClick={clearSearch}>清空搜索</button>
        </div>
      )}
    </section>
  );
}
