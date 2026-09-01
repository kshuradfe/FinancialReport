import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import type { SearchItem } from '../lib/types';
import { Icon } from './ui';

/** Type-ahead over every Yahoo-covered exchange; picking a hit appends its ticker. */
export function SymbolSearch({ onPick }: { onPick: (symbol: string) => void }) {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<SearchItem[]>([]);
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) {
      setItems([]);
      return;
    }
    const timer = setTimeout(() => {
      abort.current?.abort();
      const controller = new AbortController();
      abort.current = controller;
      setBusy(true);
      api
        .search(term, controller.signal)
        .then((r) => setItems(r.items))
        .catch(() => undefined)
        .finally(() => setBusy(false));
    }, 260);
    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="field">
      <label className="field__label">
        <span>按公司名查找代码</span>
        {busy && <span className="field__value">搜索中…</span>}
      </label>
      <input
        className="input"
        placeholder="例如 台积电 / Nestle / Toyota"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {items.length > 0 && (
        <div className="suggest">
          {items.map((it) => (
            <button
              key={it.symbol}
              className="suggest__item"
              onClick={() => {
                onPick(it.symbol);
                setQuery('');
                setItems([]);
              }}
            >
              <Icon.search size={11} />
              <span className="suggest__sym">{it.symbol}</span>
              <span className="suggest__name">{it.name}</span>
              <span className="suggest__mkt">{it.market || it.exchange}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
