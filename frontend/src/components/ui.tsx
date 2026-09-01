import { useState, type ReactNode } from 'react';

/* ------------------------------------------------------------------ icons */
type IconProps = { size?: number; className?: string };

const svg = (size: number, children: ReactNode, className?: string) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 16 16"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.4"
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    {children}
  </svg>
);

export const Icon = {
  caret: ({ size = 12, className }: IconProps) => svg(size, <path d="M6 3.5 10.5 8 6 12.5" />, className),
  play: ({ size = 13, className }: IconProps) => svg(size, <path d="M4.5 3.2v9.6L13 8Z" />, className),
  stop: ({ size = 13, className }: IconProps) => svg(size, <rect x="4.2" y="4.2" width="7.6" height="7.6" rx="1.2" />, className),
  download: ({ size = 13, className }: IconProps) =>
    svg(size, <><path d="M8 2.5v7.5M4.8 7.2 8 10.4l3.2-3.2" /><path d="M2.8 12.5h10.4" /></>, className),
  search: ({ size = 13, className }: IconProps) =>
    svg(size, <><circle cx="7.2" cy="7.2" r="4.2" /><path d="m10.4 10.4 2.8 2.8" /></>, className),
  sun: ({ size = 14, className }: IconProps) =>
    svg(size, <><circle cx="8" cy="8" r="3.1" /><path d="M8 1.4v1.6M8 13v1.6M1.4 8h1.6M13 8h1.6M3.4 3.4l1.1 1.1M11.5 11.5l1.1 1.1M12.6 3.4l-1.1 1.1M4.5 11.5l-1.1 1.1" /></>, className),
  moon: ({ size = 14, className }: IconProps) =>
    svg(size, <path d="M13 9.4A5.6 5.6 0 0 1 6.6 3a5.6 5.6 0 1 0 6.4 6.4Z" />, className),
  table: ({ size = 18, className }: IconProps) =>
    svg(size, <><rect x="2.2" y="3.2" width="11.6" height="9.6" rx="1.4" /><path d="M2.2 6.4h11.6M6.4 6.4v6.4" /></>, className),
  layers: ({ size = 18, className }: IconProps) =>
    svg(size, <><path d="M8 2.2 14 5.4 8 8.6 2 5.4Z" /><path d="m2 8.8 6 3.2 6-3.2" /></>, className),
  x: ({ size = 12, className }: IconProps) => svg(size, <path d="m4 4 8 8M12 4l-8 8" />, className),
  reset: ({ size = 13, className }: IconProps) =>
    svg(size, <><path d="M3 8a5 5 0 1 0 1.5-3.6" /><path d="M3 2.6V5h2.4" /></>, className),
};

/* ---------------------------------------------------------------- section */
export function Section({
  title,
  summary,
  defaultOpen = true,
  children,
}: {
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="section">
      <button className="section__head" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="section__caret" data-open={open}>
          <Icon.caret />
        </span>
        <span className="section__title">{title}</span>
        {summary && !open && <span className="section__summary">{summary}</span>}
      </button>
      {open && <div className="section__body">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ field */
export function Field({
  label,
  value,
  children,
}: {
  label: string;
  value?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label className="field__label">
        <span>{label}</span>
        {value !== undefined && <span className="field__value">{value}</span>}
      </label>
      {children}
    </div>
  );
}

/* -------------------------------------------------------------- segmented */
export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { key: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="segmented" role="tablist">
      {options.map((o) => (
        <button
          key={o.key}
          role="tab"
          aria-selected={value === o.key}
          className="segmented__item"
          data-active={value === o.key}
          onClick={() => onChange(o.key)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ----------------------------------------------------------------- switch */
export function Switch({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint?: string;
}) {
  return (
    <div>
      <div
        className="switch"
        data-on={checked}
        role="switch"
        aria-checked={checked}
        tabIndex={0}
        onClick={() => onChange(!checked)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onChange(!checked);
          }
        }}
      >
        <span className="switch__track" />
        <span className="switch__label">{label}</span>
      </div>
      {hint && <div className="switch__hint" style={{ marginTop: 3, marginLeft: 37 }}>{hint}</div>}
    </div>
  );
}

/* ----------------------------------------------------------------- slider */
export function Slider({
  min,
  max,
  step = 1,
  value,
  onChange,
}: {
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <input
      className="slider"
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
    />
  );
}

/* ------------------------------------------------------------------ empty */
export function Empty({ title, body, glyph }: { title: string; body: string; glyph?: ReactNode }) {
  return (
    <div className="empty">
      <div className="empty__glyph">{glyph ?? <Icon.table />}</div>
      <div className="empty__title">{title}</div>
      <div className="empty__body">{body}</div>
    </div>
  );
}
