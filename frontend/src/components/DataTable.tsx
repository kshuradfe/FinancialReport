import { useMemo } from 'react';
import { cellTone, formatCell } from '../lib/format';
import type { FieldDef, Row } from '../lib/types';

const NUMERIC = new Set(['money', 'number', 'percent', 'ratio']);

export function DataTable({
  columns,
  rows,
  fieldMap,
  sort,
  desc,
  onSort,
}: {
  columns: string[];
  rows: Row[];
  fieldMap: Record<string, FieldDef>;
  sort?: string;
  desc?: boolean;
  onSort?: (key: string) => void;
}) {
  // symbol/name pin to the left so a wide field selection stays navigable
  const ordered = useMemo(() => {
    const pinned: string[] = columns.filter((c) => c === 'symbol' || c === 'name');
    return [...pinned, ...columns.filter((c) => !pinned.includes(c))];
  }, [columns]);

  return (
    <div className="tablewrap">
      <table className="dtable">
        <thead>
          <tr>
            {ordered.map((key, i) => {
              const f = fieldMap[key];
              const numeric = NUMERIC.has(f?.fmt ?? '');
              return (
                <th
                  key={key}
                  data-numeric={numeric}
                  data-sorted={sort === key}
                  className={i === 0 ? 'sticky-col' : undefined}
                >
                  <button onClick={() => onSort?.(key)} title={f?.label_en ?? key}>
                    {f?.label_zh ?? key}
                    {sort === key && <span aria-hidden>{desc ? '↓' : '↑'}</span>}
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${row.symbol}-${row.report_date}-${idx}`}>
              {ordered.map((key, i) => {
                const f = fieldMap[key];
                const value = row[key] ?? null;
                const numeric = NUMERIC.has(f?.fmt ?? '');
                return (
                  <td
                    key={key}
                    data-numeric={numeric}
                    data-tone={cellTone(value, f)}
                    className={[
                      i === 0 ? 'sticky-col' : '',
                      value === null || value === '' ? 'is-null' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    {key === 'symbol' ? (
                      <span className="cell-symbol">{String(value ?? '—')}</span>
                    ) : key === 'period_type' ? (
                      <span className="tag">{String(value ?? '—')}</span>
                    ) : (
                      formatCell(value, f)
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
