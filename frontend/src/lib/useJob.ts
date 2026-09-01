import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api';
import type { JobConfig, JobSummary, LogEntry, Progress, UniverseItem } from './types';

const IDLE: Progress = {
  status: 'queued',
  total: 0,
  completed: 0,
  succeeded: 0,
  failed: 0,
  rows: 0,
  message: '',
};

const TERMINAL = new Set(['done', 'cancelled', 'error']);

/**
 * Owns one collection run: starts it, follows the SSE stream, and refreshes
 * the result page as rows land.
 */
export function useJob() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<Progress>(IDLE);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [universe, setUniverse] = useState<UniverseItem[]>([]);
  const [summary, setSummary] = useState<JobSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [tick, setTick] = useState(0);
  const source = useRef<EventSource | null>(null);

  // keeps the SSE error handler looking at the latest status
  const progressRef = useRef(progress);
  useEffect(() => {
    progressRef.current = progress;
  }, [progress]);

  const closeStream = useCallback(() => {
    source.current?.close();
    source.current = null;
  }, []);

  useEffect(() => closeStream, [closeStream]);

  const start = useCallback(
    async (config: JobConfig) => {
      setStarting(true);
      setError(null);
      setLogs([]);
      setUniverse([]);
      setSummary(null);
      setProgress({ ...IDLE, status: 'discovering', message: '正在构建股票池…' });
      closeStream();

      try {
        const job = await api.createJob(config);
        setJobId(job.id);

        const es = new EventSource(api.eventsUrl(job.id));
        source.current = es;

        es.addEventListener('progress', (e) => {
          setProgress(JSON.parse((e as MessageEvent).data));
          setTick((t) => t + 1);
        });
        es.addEventListener('log', (e) => {
          const entry = JSON.parse((e as MessageEvent).data) as LogEntry;
          setLogs((prev) => (prev.length > 600 ? [...prev.slice(-400), entry] : [...prev, entry]));
        });
        es.addEventListener('universe', (e) => {
          setUniverse(JSON.parse((e as MessageEvent).data).items ?? []);
        });
        es.addEventListener('done', (e) => {
          const done = JSON.parse((e as MessageEvent).data) as JobSummary;
          setSummary(done);
          setProgress((p) => ({ ...p, status: done.status, message: done.message }));
          setTick((t) => t + 1);
          closeStream();
        });
        es.onerror = () => {
          // the stream ends with the job; only surface a failure if it died early
          if (!TERMINAL.has(progressRef.current.status)) {
            setError('与后端的实时连接中断，请检查服务是否仍在运行');
          }
          closeStream();
        };
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setProgress({ ...IDLE, status: 'error' });
      } finally {
        setStarting(false);
      }
    },
    [closeStream],
  );

  const cancel = useCallback(async () => {
    if (!jobId) return;
    try {
      await api.cancelJob(jobId);
    } catch {
      /* already finished */
    }
  }, [jobId]);

  const running = !TERMINAL.has(progress.status) && jobId !== null;

  return { jobId, progress, logs, universe, summary, error, starting, running, tick, start, cancel, setError };
}
