import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './lib/api';
import { capLabel, capSteps, formatMoney } from './lib/format';
import type { FieldDef, JobConfig, Meta, Row, UniverseItem } from './lib/types';
import { useJob } from './lib/useJob';
import { DataTable } from './components/DataTable';
import { FieldPicker } from './components/FieldPicker';
import { MarketPicker } from './components/MarketPicker';
import { SymbolSearch } from './components/SymbolSearch';
import { Empty, Field, Icon, Section, Segmented, Slider, Switch } from './components/ui';

const PAGE_SIZE = 200;
const STORAGE_KEY = 'finscope.config.v1';

const DEFAULT_CONFIG: JobConfig = {
  source: 'screener',
  regions: ['us'],
  limit_per_market: 30,
  offset: 0,
  min_market_cap: 1e9,
  max_market_cap: null,
  sectors: null,
  domestic_only: true,
  local_currency_only: false,
  sort_by: 'market_cap',
  sort_asc: false,
  custom_symbols: '',
  fields: [],
  period_mode: 'auto',
  periods: 8,
  date_from: null,
  date_to: null,
  concurrency: 6,
  request_delay: 0.15,
};

type Tab = 'results' | 'universe' | 'logs';

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [config, setConfig] = useState<JobConfig>(DEFAULT_CONFIG);
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('finscope.theme') as 'light' | 'dark') ?? 'light',
  );
  const [tab, setTab] = useState<Tab>('results');
  const [rows, setRows] = useState<Row[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [rowTotal, setRowTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState<string | undefined>();
  const [desc, setDesc] = useState(true);
  const [filter, setFilter] = useState('');

  const job = useJob();

  /* ------------------------------------------------------------- theme */
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('finscope.theme', theme);
  }, [theme]);

  /* -------------------------------------------------------------- meta */
  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setMeta(m);
        setConfig((c) => {
          const stored = localStorage.getItem(STORAGE_KEY);
          const base = stored ? { ...c, ...(JSON.parse(stored) as Partial<JobConfig>) } : c;
          return {
            ...base,
            fields: base.fields?.length
              ? base.fields
              : m.fields.fields.filter((f) => f.default).map((f) => f.key),
          };
        });
      })
      .catch((e) => setMetaError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (meta) localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }, [config, meta]);

  const fieldMap = useMemo(() => {
    const map: Record<string, FieldDef> = {};
    meta?.fields.fields.forEach((f) => (map[f.key] = f));
    return map;
  }, [meta]);

  const patch = useCallback(
    (delta: Partial<JobConfig>) => setConfig((c) => ({ ...c, ...delta })),
    [],
  );

  /* -------------------------------------------------------------- rows */
  const loadRows = useCallback(async () => {
    if (!job.jobId) return;
    try {
      const data = await api.rows(job.jobId, {
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
        sort,
        desc,
        q: filter || undefined,
      });
      setRows(data.rows);
      setColumns(data.columns);
      setRowTotal(data.total);
    } catch {
      /* job may have been evicted */
    }
  }, [job.jobId, page, sort, desc, filter]);

  useEffect(() => {
    void loadRows();
  }, [loadRows, job.tick]);

  useEffect(() => setPage(0), [sort, desc, filter]);

  const onSort = (key: string) => {
    if (sort === key) setDesc((d) => !d);
    else {
      setSort(key);
      setDesc(true);
    }
  };

  /* --------------------------------------------------------- launching */
  const canRun =
    !job.running &&
    (config.source === 'custom'
      ? config.custom_symbols.trim().length > 0
      : config.regions.length > 0 || config.custom_symbols.trim().length > 0);

  const run = () => {
    setRows([]);
    setRowTotal(0);
    setPage(0);
    setSort(undefined);
    setFilter('');
    setTab('logs');
    void job.start(config);
  };

  useEffect(() => {
    if (job.progress.rows > 0 && tab === 'logs') setTab('results');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.progress.rows > 0]);

  const estimated = useMemo(() => {
    if (config.source === 'custom') {
      return config.custom_symbols.split(/[\s,;\n]+/).filter(Boolean).length;
    }
    return config.regions.length * config.limit_per_market;
  }, [config]);

  const pct =
    job.progress.total > 0 ? (job.progress.completed / job.progress.total) * 100 : job.running ? 6 : 0;

  const statusTone =
    job.progress.status === 'done'
      ? 'ok'
      : job.progress.status === 'error'
        ? 'err'
        : job.running
          ? 'run'
          : 'idle';

  if (metaError) {
    return (
      <div className="app">
        <div className="empty">
          <div className="empty__glyph">
            <Icon.x size={18} />
          </div>
          <div className="empty__title">连接不到后端</div>
          <div className="empty__body">
            {metaError}
            <br />
            请先启动 API：<code className="mono">python -m uvicorn backend.app.main:app --port 8787</code>
          </div>
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="app">
        <div className="empty">
          <div className="empty__body">加载中…</div>
        </div>
      </div>
    );
  }

  const capIndexMin = capSteps.indexOf(config.min_market_cap ?? 0);
  const capIndexMax =
    config.max_market_cap === null ? capSteps.length - 1 : capSteps.indexOf(config.max_market_cap);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark">
            Fin<span>Scope</span>
          </span>
          <span className="brand__tag">全球财报数据采集台</span>
        </div>

        <span className="status" data-tone={statusTone}>
          <span className="status__dot" />
          {job.progress.message ||
            (job.running ? '运行中' : job.progress.status === 'done' ? '已完成' : '待运行')}
        </span>

        <div className="topbar__spacer" />

        <button
          className="btn btn--ghost btn--icon"
          onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          title={theme === 'light' ? '切换到深色' : '切换到浅色'}
        >
          {theme === 'light' ? <Icon.moon /> : <Icon.sun />}
        </button>

        {pct > 0 && <div className="topbar__progress" style={{ width: `${pct}%` }} />}
      </header>

      <div className="shell">
        {/* ============================ config rail ============================ */}
        <aside className="config">
          <Section title="1 · 数据来源" summary={config.source === 'screener' ? '市场筛选' : '自定义清单'}>
            <Segmented
              value={config.source}
              onChange={(v) => patch({ source: v })}
              options={[
                { key: 'screener', label: '按市场筛选' },
                { key: 'custom', label: '自定义代码' },
              ]}
            />
            {config.source === 'custom' ? (
              <>
                <Field label="股票代码" value={`${estimated} 个`}>
                  <textarea
                    className="textarea"
                    placeholder={'AAPL\nNESN.SW\n7203.T\n600519.SS'}
                    value={config.custom_symbols}
                    onChange={(e) => patch({ custom_symbols: e.target.value })}
                  />
                </Field>
                <SymbolSearch
                  onPick={(s) =>
                    patch({
                      custom_symbols: config.custom_symbols
                        ? `${config.custom_symbols.trimEnd()}\n${s}`
                        : s,
                    })
                  }
                />
              </>
            ) : (
              <div className="switch__hint">
                通过 Yahoo 全球股票筛选器实时枚举各交易所成分股，无需维护本地代码表。
              </div>
            )}
          </Section>

          {config.source === 'screener' && (
            <>
              <Section
                title="2 · 市场范围"
                summary={`${config.regions.length} 个市场`}
              >
                <MarketPicker
                  markets={meta.markets}
                  groupOrder={meta.group_order}
                  selected={config.regions}
                  onChange={(regions) => patch({ regions })}
                />
              </Section>

              <Section
                title="3 · 抓取范围"
                summary={`每市场 ${config.limit_per_market} 只`}
              >
                <Field label="每个市场抓取数量" value={`${config.limit_per_market} 只`}>
                  <Slider
                    min={5}
                    max={500}
                    step={5}
                    value={config.limit_per_market}
                    onChange={(v) => patch({ limit_per_market: v })}
                  />
                </Field>

                <Field label="跳过前 N 名（分批抓取用）" value={`${config.offset}`}>
                  <Slider
                    min={0}
                    max={1000}
                    step={10}
                    value={config.offset}
                    onChange={(v) => patch({ offset: v })}
                  />
                </Field>

                <div className="grid-2">
                  <Field label="市值下限" value={capLabel(Math.max(0, capIndexMin))}>
                    <Slider
                      min={0}
                      max={capSteps.length - 2}
                      value={Math.max(0, capIndexMin)}
                      onChange={(i) =>
                        patch({ min_market_cap: capSteps[i] === 0 ? null : capSteps[i] })
                      }
                    />
                  </Field>
                  <Field label="市值上限" value={capLabel(Math.max(0, capIndexMax))}>
                    <Slider
                      min={1}
                      max={capSteps.length - 1}
                      value={capIndexMax < 0 ? capSteps.length - 1 : capIndexMax}
                      onChange={(i) =>
                        patch({
                          max_market_cap: capSteps[i] === Infinity ? null : capSteps[i],
                        })
                      }
                    />
                  </Field>
                </div>

                <Field label="行业板块（不选＝全部）">
                  <div className="chips">
                    {meta.sectors.map((s) => {
                      const on = config.sectors?.includes(s) ?? false;
                      return (
                        <button
                          key={s}
                          className="chip"
                          data-active={on}
                          onClick={() => {
                            const next = on
                              ? (config.sectors ?? []).filter((x) => x !== s)
                              : [...(config.sectors ?? []), s];
                            patch({ sectors: next.length ? next : null });
                          }}
                        >
                          {s}
                        </button>
                      );
                    })}
                  </div>
                </Field>

                <Field label="排序依据">
                  <div className="row">
                    <select
                      className="select"
                      value={config.sort_by}
                      onChange={(e) => patch({ sort_by: e.target.value })}
                    >
                      {meta.sort_options.map((o) => (
                        <option key={o.key} value={o.key}>
                          {o.label_zh}
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn btn--sm"
                      onClick={() => patch({ sort_asc: !config.sort_asc })}
                      style={{ flex: 'none' }}
                    >
                      {config.sort_asc ? '升序' : '降序'}
                    </button>
                  </div>
                </Field>

                <Switch
                  checked={config.domestic_only}
                  onChange={(v) => patch({ domestic_only: v })}
                  label="剔除跨境上市与重复挂牌"
                  hint="按换手率识别并丢弃外国公司的挂牌线（如瑞士交易所的 AAPL.SW），同时合并同一公司的多条挂牌线（HSBA.L / HSBAL.XC）。"
                />

                <Switch
                  checked={config.local_currency_only}
                  onChange={(v) => patch({ local_currency_only: v })}
                  label="只保留以本地货币记账的公司"
                  hint="德国、意大利、巴西这类市场靠它才能彻底滤净美股挂牌线；但英国的汇丰、壳牌用美元编报，开启后会被一并排除。"
                />

                <Field label="补充自定义代码（可选）">
                  <textarea
                    className="textarea"
                    style={{ minHeight: 52 }}
                    placeholder="追加到筛选结果之后，例如 BRK-B"
                    value={config.custom_symbols}
                    onChange={(e) => patch({ custom_symbols: e.target.value })}
                  />
                </Field>
              </Section>
            </>
          )}

          <Section title="4 · 报告期范围" summary={`${config.periods} 期`}>
            <Field label="报表口径">
              <Segmented
                value={config.period_mode}
                onChange={(v) => patch({ period_mode: v })}
                options={[
                  { key: 'auto', label: '自动' },
                  { key: 'quarterly', label: '季报' },
                  { key: 'annual', label: '年报' },
                ]}
              />
            </Field>
            <div className="switch__hint" style={{ marginTop: -6 }}>
              自动模式优先取季报；欧洲、澳洲等半年报市场会自动回退到年报——原脚本正是卡在这里。
            </div>

            <Field label="每只股票取几期" value={`最近 ${config.periods} 期`}>
              <Slider
                min={1}
                max={20}
                value={config.periods}
                onChange={(v) => patch({ periods: v })}
              />
            </Field>

            <div className="grid-2">
              <Field label="起始日期">
                <input
                  className="input"
                  type="date"
                  value={config.date_from ?? ''}
                  onChange={(e) => patch({ date_from: e.target.value || null })}
                />
              </Field>
              <Field label="截止日期">
                <input
                  className="input"
                  type="date"
                  value={config.date_to ?? ''}
                  onChange={(e) => patch({ date_to: e.target.value || null })}
                />
              </Field>
            </div>
            {(config.date_from || config.date_to) && (
              <button
                className="link-btn"
                onClick={() => patch({ date_from: null, date_to: null })}
              >
                清除日期区间
              </button>
            )}
          </Section>

          <Section title="5 · 数据字段" summary={`${config.fields.length} 项`} defaultOpen={false}>
            <FieldPicker
              groups={meta.fields.groups}
              fields={meta.fields.fields}
              selected={config.fields}
              onChange={(fields) => patch({ fields })}
            />
          </Section>

          <Section title="6 · 抓取参数" summary={`${config.concurrency} 并发`} defaultOpen={false}>
            <Field label="并发数" value={`${config.concurrency}`}>
              <Slider
                min={1}
                max={16}
                value={config.concurrency}
                onChange={(v) => patch({ concurrency: v })}
              />
            </Field>
            <Field label="每次请求间隔" value={`${config.request_delay.toFixed(2)}s`}>
              <Slider
                min={0}
                max={2}
                step={0.05}
                value={config.request_delay}
                onChange={(v) => patch({ request_delay: v })}
              />
            </Field>
            <div className="switch__hint">
              并发越高越快，但 Yahoo 会限流。10 以上建议把间隔提到 0.3 秒以上。
            </div>
            <button
              className="btn btn--sm"
              onClick={() =>
                setConfig({
                  ...DEFAULT_CONFIG,
                  fields: meta.fields.fields.filter((f) => f.default).map((f) => f.key),
                })
              }
            >
              <Icon.reset /> 恢复默认设置
            </button>
          </Section>
        </aside>

        {/* ============================= workspace ============================= */}
        <section className="workspace">
          <div className="runbar">
            {job.running ? (
              <button className="btn btn--danger" onClick={() => void job.cancel()}>
                <Icon.stop /> 停止
              </button>
            ) : (
              <button className="btn btn--primary" onClick={run} disabled={!canRun}>
                <Icon.play /> 开始抓取
              </button>
            )}

            <div className="statdivider" />

            <div className="stat">
              <span className="stat__value">
                {job.progress.completed}
                <span style={{ color: 'var(--text-3)', fontSize: 11 }}>
                  /{job.progress.total || estimated}
                </span>
              </span>
              <span className="stat__label">已处理</span>
            </div>
            <div className="stat stat--pos">
              <span className="stat__value">{job.progress.succeeded}</span>
              <span className="stat__label">成功</span>
            </div>
            <div className={`stat${job.progress.failed ? ' stat--neg' : ''}`}>
              <span className="stat__value">{job.progress.failed}</span>
              <span className="stat__label">失败</span>
            </div>
            <div className="stat">
              <span className="stat__value">{rowTotal || job.progress.rows}</span>
              <span className="stat__label">数据行</span>
            </div>

            <div className="topbar__spacer" />

            <input
              className="input"
              style={{ width: 168 }}
              placeholder="筛选代码或名称…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />

            <ExportMenu jobId={job.jobId} enabled={(rowTotal || job.progress.rows) > 0} />
          </div>

          {job.error && (
            <div style={{ padding: '10px 18px 0' }}>
              <div className="banner">
                <Icon.x size={13} />
                <span>{job.error}</span>
              </div>
            </div>
          )}

          <div className="tabs">
            {(
              [
                ['results', '结果', rowTotal || job.progress.rows],
                ['universe', '股票池', job.universe.length],
                ['logs', '运行日志', job.logs.length],
              ] as const
            ).map(([key, label, count]) => (
              <button
                key={key}
                className="tab"
                data-active={tab === key}
                onClick={() => setTab(key as Tab)}
              >
                {label}
                {count > 0 && <span className="tab__badge">{count}</span>}
              </button>
            ))}
            {tab === 'results' && rowTotal > PAGE_SIZE && (
              <div className="tabs__actions">
                <button
                  className="btn btn--sm btn--ghost"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                >
                  上一页
                </button>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                  {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, rowTotal)} / {rowTotal}
                </span>
                <button
                  className="btn btn--sm btn--ghost"
                  disabled={(page + 1) * PAGE_SIZE >= rowTotal}
                  onClick={() => setPage((p) => p + 1)}
                >
                  下一页
                </button>
              </div>
            )}
          </div>

          {tab === 'results' &&
            (rows.length > 0 ? (
              <DataTable
                columns={columns}
                rows={rows}
                fieldMap={fieldMap}
                sort={sort}
                desc={desc}
                onSort={onSort}
              />
            ) : (
              <Empty
                title={job.running ? '正在抓取…' : '还没有数据'}
                body={
                  job.running
                    ? '第一批结果稍后会出现在这里。'
                    : '在左侧选好市场、范围和字段，然后点“开始抓取”。默认设置会取美国市值前 30 大公司最近 8 期财报。'
                }
              />
            ))}

          {tab === 'universe' && <UniverseTable items={job.universe} />}

          {tab === 'logs' && <LogView logs={job.logs} />}

          <div className="footer">
            <span>
              覆盖 {meta.markets.filter((m) => m.available).length} 个市场 · {meta.fields.fields.length} 个字段
            </span>
            <span style={{ marginLeft: 'auto' }}>
              数据来源 Yahoo Finance（yfinance）· 仅供研究，不构成投资建议
            </span>
          </div>
        </section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ export */
function ExportMenu({ jobId, enabled }: { jobId: string | null; enabled: boolean }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const formats: { key: 'csv' | 'xlsx' | 'json'; label: string }[] = [
    { key: 'csv', label: 'CSV（中文表头 / Excel 友好）' },
    { key: 'xlsx', label: 'Excel 工作簿' },
    { key: 'json', label: 'JSON' },
  ];

  return (
    <div style={{ position: 'relative' }} ref={box}>
      <button
        className="btn"
        disabled={!enabled || !jobId}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon.download /> 导出
      </button>
      {open && jobId && (
        <div
          className="suggest"
          style={{ position: 'absolute', right: 0, top: 34, width: 236, zIndex: 30 }}
        >
          {formats.map((f) => (
            <a
              key={f.key}
              className="suggest__item"
              href={api.exportUrl(jobId, f.key, f.key === 'json' ? 'key' : 'zh')}
              onClick={() => setOpen(false)}
            >
              <span className="suggest__name" style={{ color: 'var(--text)' }}>{f.label}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- universe */
function UniverseTable({ items }: { items: UniverseItem[] }) {
  if (items.length === 0) {
    return (
      <Empty
        title="股票池为空"
        body="运行任务后，这里会列出实际命中的标的，方便你确认筛选条件是否合理。"
        glyph={<Icon.layers />}
      />
    );
  }
  return (
    <div className="tablewrap">
      <table className="dtable">
        <thead>
          <tr>
            <th className="sticky-col">
              <button>代码</button>
            </th>
            <th>
              <button>名称</button>
            </th>
            <th>
              <button>交易所</button>
            </th>
            <th data-numeric>
              <button>市值</button>
            </th>
            <th data-numeric>
              <button>市盈率</button>
            </th>
            <th data-numeric>
              <button>股价</button>
            </th>
            <th>
              <button>货币</button>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.symbol}>
              <td className="sticky-col">
                <span className="cell-symbol">{it.symbol}</span>
              </td>
              <td>{it.name || '—'}</td>
              <td className="muted">{it.exchange || '—'}</td>
              <td data-numeric>{it.market_cap ? formatMoney(it.market_cap) : '—'}</td>
              <td data-numeric>{it.trailing_pe ? it.trailing_pe.toFixed(1) : '—'}</td>
              <td data-numeric>{it.price ? it.price.toFixed(2) : '—'}</td>
              <td>
                <span className="tag">{it.quote_currency ?? '—'}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* -------------------------------------------------------------------- logs */
function LogView({ logs }: { logs: { t: string; level: string; text: string }[] }) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' });
  }, [logs.length]);

  if (logs.length === 0) {
    return <Empty title="暂无日志" body="任务开始后，每只股票的抓取结果会实时打印在这里。" />;
  }
  return (
    <div className="logs">
      {logs.map((l, i) => (
        <div className="log" data-level={l.level} key={i}>
          <span className="log__t">{l.t}</span>
          <span className="log__text">{l.text}</span>
        </div>
      ))}
      <div ref={end} />
    </div>
  );
}
