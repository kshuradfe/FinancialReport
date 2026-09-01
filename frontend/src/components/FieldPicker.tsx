import { useState } from 'react';
import type { FieldDef, FieldGroup } from '../lib/types';
import { Icon } from './ui';

const PRESETS: { label: string; pick: (fields: FieldDef[]) => string[] }[] = [
  { label: '核心', pick: (f) => f.filter((x) => x.default).map((x) => x.key) },
  { label: '全部', pick: (f) => f.map((x) => x.key) },
  {
    label: '仅估值',
    pick: (f) => f.filter((x) => x.group === 'identity' || x.group === 'quote').map((x) => x.key),
  },
  {
    label: '三大报表',
    pick: (f) =>
      f
        .filter((x) => ['identity', 'balance', 'income', 'cashflow'].includes(x.group))
        .map((x) => x.key),
  },
  {
    label: '比率分析',
    pick: (f) => f.filter((x) => ['identity', 'computed', 'quote'].includes(x.group)).map((x) => x.key),
  },
];

export function FieldPicker({
  groups,
  fields,
  selected,
  onChange,
}: {
  groups: FieldGroup[];
  fields: FieldDef[];
  selected: string[];
  onChange: (keys: string[]) => void;
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({ identity: true, income: true });
  const set = new Set(selected);

  const toggle = (key: string, mandatory: boolean) => {
    if (mandatory) return;
    onChange(set.has(key) ? selected.filter((k) => k !== key) : [...selected, key]);
  };

  return (
    <>
      <div className="market__quick">
        {PRESETS.map((p) => (
          <button key={p.label} className="chip" onClick={() => onChange(p.pick(fields))}>
            {p.label}
          </button>
        ))}
      </div>

      {groups.map((g) => {
        const items = fields.filter((f) => f.group === g.key);
        if (items.length === 0) return null;
        const on = items.filter((f) => set.has(f.key)).length;
        const isOpen = open[g.key] ?? false;
        return (
          <div className="fieldgroup" key={g.key}>
            <button
              className="fieldgroup__head"
              onClick={() => setOpen((o) => ({ ...o, [g.key]: !isOpen }))}
            >
              <span className="section__caret" data-open={isOpen}>
                <Icon.caret size={11} />
              </span>
              <span className="fieldgroup__title">{g.label_zh}</span>
              <span className="fieldgroup__meta">
                {on}/{items.length}
              </span>
            </button>
            {isOpen && (
              <div className="fieldgroup__body">
                <button
                  className="link-btn"
                  style={{ width: '100%', textAlign: 'left', marginBottom: 4 }}
                  onClick={() => {
                    const keys = items.filter((f) => !f.mandatory).map((f) => f.key);
                    onChange(
                      on === items.length
                        ? selected.filter((k) => !keys.includes(k))
                        : [...new Set([...selected, ...keys])],
                    );
                  }}
                >
                  {on === items.length ? '取消本组' : '全选本组'}
                </button>
                {items.map((f) => (
                  <button
                    key={f.key}
                    className={`chip chip--field${f.mandatory ? ' chip--locked' : ''}`}
                    data-active={set.has(f.key) && !f.mandatory}
                    onClick={() => toggle(f.key, f.mandatory)}
                    title={`${f.label_en}${f.mandatory ? '（必选）' : ''}`}
                  >
                    {f.label_zh}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}
