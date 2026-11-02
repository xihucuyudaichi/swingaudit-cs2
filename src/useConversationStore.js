import { useEffect, useMemo, useState } from 'react';

const PREFIX = 'swingaudit.conversation.v1:';
const validTurn = value => value && typeof value.answer === 'string' && Array.isArray(value.tools);
function load(scope, fallback) {
  try {
    const entry = JSON.parse(localStorage.getItem(PREFIX + scope));
    const d = entry?.data;
    if (entry?.version !== 1 || !d || typeof d.q !== 'string') return fallback;
    if ('result' in fallback && d.result !== null && !validTurn(d.result)) return fallback;
    if ('turns' in fallback && (!Array.isArray(d.turns) || !d.turns.every(validTurn) || !Number.isInteger(d.activeTurnIdx))) return fallback;
    return { ...fallback, ...d };
  } catch { return fallback; }
}

export function useConversationStore(scope, fallback) {
  const restored = useMemo(() => load(scope, fallback), [scope]);
  const [entry, setEntry] = useState(() => ({ scope, data: restored }));
  const [storageError, setStorageError] = useState('');
  const data = entry.scope === scope ? entry.data : restored;
  useEffect(() => {
    if (entry.scope !== scope) setEntry({ scope, data: restored });
  }, [scope, restored, entry.scope]);
  useEffect(() => {
    if (entry.scope !== scope) return;
    try {
      localStorage.setItem(PREFIX + scope, JSON.stringify({ version: 1, data: entry.data }));
      setStorageError('');
    } catch {
      setStorageError('浏览器未能自动保存本次对话，请使用“保存研究”保留重要结果。');
    }
  }, [scope, entry]);
  function update(patch) {
    setEntry(old => {
      const current = old.scope === scope ? old.data : restored;
      return { scope, data: { ...current, ...(typeof patch === 'function' ? patch(current) : patch) } };
    });
  }
  return [data, update, storageError];
}
