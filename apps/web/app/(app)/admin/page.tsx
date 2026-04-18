'use client';

import { Card, CardBody } from '@axis/design-system';

const KPIS: ReadonlyArray<{ label: string; value: string; delta?: string }> = [
  { label: 'Indexing backlog',     value: '—' },
  { label: 'Avg run latency',      value: '—' },
  { label: 'Error rate',           value: '—' },
  { label: 'Connector uptime',     value: '—' },
  { label: 'Active runs',          value: '—' },
];

export default function AdminPage() {
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Admin</h1>
        <p className="text-body text-ink-secondary">
          System health, connector matrix, eval trends. Backend metrics land in Plan 8.
        </p>
      </header>

      <section aria-labelledby="system-health">
        <h2 id="system-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          System health
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          {KPIS.map((k) => (
            <Card key={k.label}>
              <CardBody className="space-y-1">
                <div className="font-display text-display-m text-ink tabular-nums">{k.value}</div>
                <div className="font-mono text-[11px] uppercase tracking-[0.06em] text-ink-tertiary">
                  {k.label}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="connector-health">
        <h2 id="connector-health" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Connector health matrix
        </h2>
        <Card>
          <CardBody className="py-10 text-center text-body-s text-ink-tertiary">
            Awaiting backend metrics endpoint.
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="eval-trends">
        <h2 id="eval-trends" className="mb-3 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Eval trends
        </h2>
        <Card>
          <CardBody className="py-10 text-center text-body-s text-ink-tertiary">
            Awaiting backend metrics endpoint.
          </CardBody>
        </Card>
      </section>
    </div>
  );
}
