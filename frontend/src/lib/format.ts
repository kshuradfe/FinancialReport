import type { FieldDef } from './types';

const UNITS: [number, string][] = [
  [1e12, '万亿'],
  [1e8, '亿'],
  [1e4, '万'],
];

/** Compact money using Chinese myriad units — 亿 reads faster than 1.2e11. */
export function formatMoney(value: number): string {
  const abs = Math.abs(value);
  for (const [scale, suffix] of UNITS) {
    if (abs >= scale) {
      const scaled = value / scale;
      return `${scaled.toFixed(Math.abs(scaled) >= 100 ? 0 : 2)}${suffix}`;
    }
  }
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

export function formatNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e4) return formatMoney(value);
  if (abs >= 100) return value.toFixed(0);
  if (abs >= 1) return value.toFixed(2);
  return value.toFixed(3);
}

export function formatCell(value: string | number | null, field?: FieldDef): string {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'string') return value;
  if (!Number.isFinite(value)) return '—';

  switch (field?.fmt) {
    case 'percent':
      return `${value.toFixed(1)}%`;
    case 'ratio':
      return `${value.toFixed(2)}×`;
    case 'money':
      return formatMoney(value);
    case 'number':
      return formatNumber(value);
    default:
      return formatNumber(value);
  }
}

/** Signed metrics get colour; neutral magnitudes stay ink-coloured. */
export function cellTone(value: string | number | null, field?: FieldDef): '' | 'pos' | 'neg' {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '';
  const signed =
    field?.fmt === 'percent' ||
    field?.key?.startsWith('cashflow_') ||
    field?.key === 'income_net_income' ||
    field?.key === 'income_operating_income' ||
    field?.key === 'income_pretax_income';
  if (!signed) return '';
  return value < 0 ? 'neg' : value > 0 ? 'pos' : '';
}

const CAP_STEPS = [0, 1e7, 5e7, 1e8, 5e8, 1e9, 5e9, 1e10, 5e10, 1e11, 5e11, 1e12, Infinity];

export const capSteps = CAP_STEPS;

export function capLabel(index: number): string {
  const v = CAP_STEPS[index];
  if (v === 0) return '不限';
  if (v === Infinity) return '不限';
  return formatMoney(v);
}
