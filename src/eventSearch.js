const normalize = value => String(value ?? '').normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();

// Search visible archive fields, never source URLs or serialized provenance.
export function buildEventIndex(seasons = {}) {
  const events = Object.entries(seasons)
    .sort(([a], [b]) => Number(b) - Number(a))
    .flatMap(([year, season]) => (season.events || []).map(event => ({
      event,
      year,
      searchText: normalize([
        year, event.name, event.name_zh, event.tier, event.city, event.location, event.venue,
        ...(event.players || []).map(player => player.team)
      ].filter(Boolean).join(' '))
    })));
  return { events };
}

export function searchEventIndex(index, query) {
  const tokens = normalize(query).trim().split(/\s+/).filter(Boolean);
  const matches = item => tokens.every(token => item.searchText.includes(token));
  return {
    events: index.events.filter(matches)
  };
}
