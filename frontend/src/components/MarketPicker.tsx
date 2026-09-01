import { useMemo, useState } from 'react';
import type { Market } from '../lib/types';
import { Icon } from './ui';

const PRESETS: { label: string; regions: string[] }[] = [
  { label: '仅美股', regions: ['us'] },
  { label: '全球七大', regions: ['us', 'cn', 'jp', 'gb', 'de', 'hk', 'in'] },
  { label: '发达市场', regions: ['us', 'ca', 'gb', 'de', 'fr', 'nl', 'ch', 'it', 'es', 'se', 'jp', 'au', 'hk', 'sg'] },
  { label: '亚太', regions: ['cn', 'hk', 'tw', 'jp', 'kr', 'in', 'sg', 'au', 'nz', 'id', 'my', 'th'] },
  { label: '欧洲', regions: ['gb', 'de', 'fr', 'nl', 'ch', 'it', 'es', 'be', 'at', 'pt', 'ie', 'gr', 'se', 'no', 'dk', 'fi'] },
  { label: '新兴市场', regions: ['cn', 'in', 'br', 'za', 'tr', 'mx', 'id', 'th', 'my', 'sa', 'pl'] },
];

export function MarketPicker({
  markets,
  groupOrder,
  selected,
  onChange,
}: {
  markets: Market[];
  groupOrder: string[];
  selected: string[];
  onChange: (regions: string[]) => void;
}) {
  const [query, setQuery] = useState('');
  const [showAll, setShowAll] = useState(false);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return markets.filter((m) => {
      if (!m.available && !showAll && !selected.includes(m.region)) return false;
      if (!needle) return true;
      return (
        m.name_zh.includes(needle) ||
        m.name_en.toLowerCase().includes(needle) ||
        m.region.includes(needle) ||
        m.currency.toLowerCase().includes(needle) ||
        m.exchanges.some((e) => e.toLowerCase().includes(needle))
      );
    });
  }, [markets, query, showAll, selected]);

  const grouped = useMemo(() => {
    const map = new Map<string, Market[]>();
    for (const m of visible) {
      if (!map.has(m.group)) map.set(m.group, []);
      map.get(m.group)!.push(m);
    }
    return groupOrder.filter((g) => map.has(g)).map((g) => [g, map.get(g)!] as const);
  }, [visible, groupOrder]);

  const toggle = (region: string) =>
    onChange(
      selected.includes(region) ? selected.filter((r) => r !== region) : [...selected, region],
    );

  const unavailableCount = markets.filter((m) => !m.available).length;

  return (
    <>
      <div className="market__search">
        <input
          className="input"
          placeholder="搜索市场、交易所或货币…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="market__quick">
        {PRESETS.map((p) => (
          <button key={p.label} className="chip" onClick={() => onChange(p.regions)}>
            {p.label}
          </button>
        ))}
        {selected.length > 0 && (
          <button className="chip" onClick={() => onChange([])}>
            <Icon.x size={10} /> 清空
          </button>
        )}
      </div>

      {grouped.map(([group, items]) => {
        const allOn = items.every((m) => selected.includes(m.region));
        return (
          <div className="market__group" key={group}>
            <div className="market__grouphead">
              <span className="eyebrow">{group}</span>
              <span className="market__count">
                {items.filter((m) => selected.includes(m.region)).length}/{items.length}
              </span>
              <button
                className="link-btn"
                style={{ marginLeft: 'auto' }}
                onClick={() =>
                  onChange(
                    allOn
                      ? selected.filter((r) => !items.some((m) => m.region === r))
                      : [...new Set([...selected, ...items.map((m) => m.region)])],
                  )
                }
              >
                {allOn ? '取消' : '全选'}
              </button>
            </div>
            <div className="chips">
              {items.map((m) => (
                <button
                  key={m.region}
                  className={`chip${m.available ? '' : ' chip--dim'}`}
                  data-active={selected.includes(m.region)}
                  onClick={() => toggle(m.region)}
                  title={`${m.name_en} · ${m.exchanges.join(' / ')} · ${m.currency}${
                    m.available ? '' : '（Yahoo 暂无成分股数据）'
                  }`}
                >
                  <span className="chip__flag">{m.flag}</span>
                  {m.name_zh}
                </button>
              ))}
            </div>
          </div>
        );
      })}

      {unavailableCount > 0 && (
        <button className="link-btn" onClick={() => setShowAll((s) => !s)}>
          {showAll ? '隐藏' : '显示'} {unavailableCount} 个暂无数据的市场
        </button>
      )}
    </>
  );
}
