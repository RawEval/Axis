'use client';

import {
  Badge,
  Button,
  PageHeader,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui';
import { clearToken } from '@/lib/auth';
import { useMe } from '@/lib/queries/auth';
import { useEvalScores } from '@/lib/queries/eval';
import { useMounted } from '@/lib/use-mounted';

export default function SettingsPage() {
  const mounted = useMounted();
  const { data: rawMe } = useMe();
  const me = mounted ? rawMe : undefined;
  const signOut = () => {
    clearToken();
    window.location.href = '/login';
  };

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-5 px-6 py-6">
      <PageHeader title="Settings" />

      <Panel>
        <PanelHeader>
          <div className="text-sm font-semibold text-ink">Account</div>
          <Badge tone="brand">{me?.plan ?? 'free'}</Badge>
        </PanelHeader>
        <PanelBody>
          <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-3">
            <dt className="label-caps">Email</dt>
            <dd className="col-span-2 text-sm text-ink">{me?.email ?? '—'}</dd>

            <dt className="label-caps">Name</dt>
            <dd className="col-span-2 text-sm text-ink">{me?.name ?? '—'}</dd>

            <dt className="label-caps">User ID</dt>
            <dd className="col-span-2 font-mono text-xs text-ink-secondary">{me?.id ?? '—'}</dd>

            <dt className="label-caps">Member since</dt>
            <dd className="col-span-2 text-sm text-ink-secondary">
              {me?.created_at ? new Date(me.created_at).toLocaleDateString() : '—'}
            </dd>
          </dl>
        </PanelBody>
      </Panel>

      <OutputQualityPanel />

      <Panel>
        <PanelHeader>
          <div className="text-sm font-semibold text-ink">Session</div>
        </PanelHeader>
        <PanelBody>
          <p className="text-sm text-ink-secondary">
            End the current session on this device. You&apos;ll need to sign in again.
          </p>
          <div className="mt-3">
            <Button variant="danger" size="sm" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </PanelBody>
      </Panel>
    </div>
  );
}

function OutputQualityPanel() {
  const { data, isLoading } = useEvalScores(50);
  const scored = data ?? [];
  const composites = scored
    .map((r) => r.composite_score)
    .filter((n): n is number => typeof n === 'number');
  const avg =
    composites.length > 0
      ? composites.reduce((a, b) => a + b, 0) / composites.length
      : null;
  const flagged = scored.filter((r) => r.flagged).length;

  return (
    <Panel>
      <PanelHeader>
        <div className="text-sm font-semibold text-ink">Output quality</div>
        <Badge tone="brand">
          {isLoading ? 'loading' : `${scored.length} runs scored`}
        </Badge>
      </PanelHeader>
      <PanelBody>
        <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-3">
          <dt className="label-caps">Average composite</dt>
          <dd className="col-span-2 text-sm text-ink">
            {avg != null ? avg.toFixed(2) : '—'}
            <span className="ml-1 text-xs text-ink-tertiary">/ 5.00</span>
          </dd>

          <dt className="label-caps">Flagged runs</dt>
          <dd className="col-span-2 text-sm text-ink-secondary">
            {flagged} of {scored.length}
          </dd>

          <dt className="label-caps">Rubric mix</dt>
          <dd className="col-span-2 text-sm text-ink-secondary">
            {Object.entries(
              scored.reduce<Record<string, number>>((acc, r) => {
                acc[r.rubric_type] = (acc[r.rubric_type] ?? 0) + 1;
                return acc;
              }, {}),
            )
              .map(([k, v]) => `${k}: ${v}`)
              .join(' · ') || '—'}
          </dd>
        </dl>
        {scored.length > 0 && (
          <div className="mt-4 flex flex-col gap-1">
            <div className="label-caps mb-1">Recent runs</div>
            {scored.slice(0, 8).map((r) => (
              <div
                key={r.id}
                className="flex items-center gap-3 rounded border border-canvas-subtle px-2.5 py-1.5 text-xs"
              >
                <Badge tone={r.flagged ? 'warning' : 'neutral'}>
                  {r.composite_score?.toFixed(2) ?? '—'}
                </Badge>
                <span className="flex-1 truncate text-ink">{r.prompt}</span>
                <span className="font-mono text-ink-tertiary">
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </PanelBody>
    </Panel>
  );
}
