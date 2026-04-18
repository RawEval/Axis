'use client';

import { Card, CardBody, Skeleton } from '@axis/design-system';
import {
  useAdminConnectors,
  useAdminEval,
  useAdminRuns,
  useAdminStats,
  type AdminEvalRow,
} from '@/lib/queries/admin';

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toLocaleString();
}

/** `avg_eval_composite` is a 0–10 score, not a fraction. Render with one decimal. */
function formatScore(n: number | null | undefined): string {
  if (n == null) return '—';
  return n.toFixed(1);
}

function formatLatency(ms: number | null | undefined): string {
  if (ms == null) return '—';
  return `${ms.toLocaleString()}ms`;
}

interface EvalSummary {
  composite: number | null;
  flagged: number;
  recent_count: number;
}

function summariseEval(rows: AdminEvalRow[] | undefined): EvalSummary {
  if (!rows || rows.length === 0) {
    return { composite: null, flagged: 0, recent_count: 0 };
  }
  let weightedSum = 0;
  let weightTotal = 0;
  let flagged = 0;
  let recent = 0;
  for (const r of rows) {
    recent += r.count;
    flagged += r.flagged;
    if (r.avg_composite != null) {
      weightedSum += r.avg_composite * r.count;
      weightTotal += r.count;
    }
  }
  return {
    composite: weightTotal > 0 ? weightedSum / weightTotal : null,
    flagged,
    recent_count: recent,
  };
}

export default function AdminPage() {
  const stats = useAdminStats();
  const connectors = useAdminConnectors();
  const runs = useAdminRuns();
  const evalQuery = useAdminEval();
  const evalSummary = summariseEval(evalQuery.data);

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Admin</h1>
        <p className="text-body text-ink-secondary">
          System health, connector matrix, eval trends.
        </p>
      </header>

      <section aria-labelledby="system-health">
        <h2
          id="system-health"
          className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
        >
          System health
        </h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <KPI
            label="Users"
            value={formatNumber(stats.data?.users)}
            loading={stats.isLoading}
          />
          <KPI
            label="Total runs"
            value={formatNumber(stats.data?.total_runs)}
            loading={stats.isLoading}
          />
          <KPI
            label="Recent runs"
            value={formatNumber(runs.data?.length)}
            loading={runs.isLoading}
          />
          <KPI
            label="Connected"
            value={formatNumber(stats.data?.connected_tools)}
            loading={stats.isLoading}
          />
          <KPI
            label="Avg latency"
            value={formatLatency(stats.data?.avg_latency_ms)}
            loading={stats.isLoading}
          />
        </div>
      </section>

      <section aria-labelledby="connector-health">
        <h2
          id="connector-health"
          className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
        >
          Connector health
        </h2>
        <Card>
          {connectors.isLoading ? (
            <CardBody>
              <Skeleton height={120} rounded="md" />
            </CardBody>
          ) : connectors.data && connectors.data.length > 0 ? (
            <ul className="divide-y divide-edge-subtle">
              {connectors.data.slice(0, 10).map((c) => (
                <li
                  key={c.id}
                  className="flex items-center gap-3 px-5 py-3"
                >
                  <span className="font-mono text-mono-s uppercase text-ink">
                    {c.tool}
                  </span>
                  <span className="font-mono text-mono-s text-ink-tertiary">
                    {c.user_email}
                  </span>
                  <span className="ml-auto font-mono text-[11px] uppercase tracking-[0.06em] text-ink-secondary">
                    {c.status}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <CardBody className="py-10 text-center text-body-s text-ink-tertiary">
              No connector data.
            </CardBody>
          )}
        </Card>
      </section>

      <section aria-labelledby="eval-summary">
        <h2
          id="eval-summary"
          className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
        >
          Eval summary
        </h2>
        <Card>
          {evalQuery.isLoading ? (
            <CardBody>
              <Skeleton height={80} rounded="md" />
            </CardBody>
          ) : (
            <CardBody className="grid grid-cols-3 gap-6">
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">
                  {formatScore(evalSummary.composite)}
                </div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                  Composite score
                </div>
              </div>
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">
                  {formatNumber(evalSummary.flagged)}
                </div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                  Flagged runs
                </div>
              </div>
              <div>
                <div className="font-display text-display-m text-ink tabular-nums">
                  {formatNumber(evalSummary.recent_count)}
                </div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                  Recent (90d)
                </div>
              </div>
            </CardBody>
          )}
        </Card>
      </section>
    </div>
  );
}

function KPI({
  label,
  value,
  loading,
}: {
  label: string;
  value: string;
  loading: boolean;
}) {
  return (
    <Card>
      <CardBody className="space-y-1">
        {loading ? (
          <Skeleton height={36} rounded="sm" />
        ) : (
          <div className="font-display text-display-m text-ink tabular-nums">
            {value}
          </div>
        )}
        <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
          {label}
        </div>
      </CardBody>
    </Card>
  );
}
