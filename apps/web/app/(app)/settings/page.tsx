'use client';

import {
  Badge,
  SegmentedControl,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@axis/design-system';
import { CapabilitiesPanel } from '@/components/settings/capabilities-panel';
import { clearToken } from '@/lib/auth';
import { useMe } from '@/lib/queries/auth';
import { useEvalScores } from '@/lib/queries/eval';
import { useTheme, type Theme } from '@/lib/theme';
import { useMounted } from '@/lib/use-mounted';

const THEME_OPTIONS = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
] as const;

export default function SettingsPage() {
  const signOut = () => {
    clearToken();
    window.location.href = '/login';
  };

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Settings</h1>
        <p className="text-body text-ink-secondary">
          Manage your account, appearance, and how Axis behaves on your behalf.
        </p>
      </header>

      <Tabs defaultValue="account">
        <TabsList>
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="capabilities">Capabilities</TabsTrigger>
          <TabsTrigger value="output">Output quality</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="account">
          <AccountTab />
        </TabsContent>

        <TabsContent value="appearance">
          <AppearanceTab />
        </TabsContent>

        <TabsContent value="capabilities">
          <CapabilitiesPanel />
        </TabsContent>

        <TabsContent value="output">
          <OutputQualityTab />
        </TabsContent>

        <TabsContent value="notifications">
          <SectionHeader>Notifications</SectionHeader>
          <p className="mt-3 text-body-s text-ink-tertiary">
            Notification preferences. Coming soon.
          </p>
        </TabsContent>

        <TabsContent value="advanced">
          <SectionHeader>Session</SectionHeader>
          <p className="mt-3 text-body-s text-ink-secondary">
            End the current session on this device. You&apos;ll need to sign in again.
          </p>
          <button
            type="button"
            onClick={signOut}
            className="mt-4 text-body-s text-danger hover:underline"
          >
            Sign out
          </button>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
      {children}
    </h2>
  );
}

function AccountTab() {
  const mounted = useMounted();
  const { data: rawMe } = useMe();
  const me = mounted ? rawMe : undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHeader>Account</SectionHeader>
        <Badge tone="accent">{me?.plan ?? 'free'}</Badge>
      </div>
      <dl className="grid grid-cols-1 gap-y-3 border-t border-edge-subtle pt-4 sm:grid-cols-3">
        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Email
        </dt>
        <dd className="col-span-2 text-body-s text-ink">{me?.email ?? '—'}</dd>

        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Name
        </dt>
        <dd className="col-span-2 text-body-s text-ink">{me?.name ?? '—'}</dd>

        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          User ID
        </dt>
        <dd className="col-span-2 font-mono text-mono-s text-ink-secondary">
          {me?.id ?? '—'}
        </dd>

        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Member since
        </dt>
        <dd className="col-span-2 text-body-s text-ink-secondary">
          {me?.created_at ? new Date(me.created_at).toLocaleDateString() : '—'}
        </dd>
      </dl>
    </div>
  );
}

function AppearanceTab() {
  const { theme, setTheme } = useTheme();
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <SectionHeader>Theme</SectionHeader>
        <SegmentedControl
          value={theme}
          onChange={(next) => setTheme(next as Theme)}
          options={THEME_OPTIONS}
        />
        <p className="text-caption text-ink-tertiary">
          System follows your OS preference.
        </p>
      </div>
    </div>
  );
}

function OutputQualityTab() {
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <SectionHeader>Output quality</SectionHeader>
        <Badge tone="accent">
          {isLoading ? 'loading' : `${scored.length} runs scored`}
        </Badge>
      </div>
      <dl className="grid grid-cols-1 gap-y-3 border-t border-edge-subtle pt-4 sm:grid-cols-3">
        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Average composite
        </dt>
        <dd className="col-span-2 text-body-s text-ink">
          {avg != null ? avg.toFixed(2) : '—'}
          <span className="ml-1 text-caption text-ink-tertiary">/ 5.00</span>
        </dd>

        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Flagged runs
        </dt>
        <dd className="col-span-2 text-body-s text-ink-secondary">
          {flagged} of {scored.length}
        </dd>

        <dt className="font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
          Rubric mix
        </dt>
        <dd className="col-span-2 text-body-s text-ink-secondary">
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
        <div className="mt-2 flex flex-col gap-1">
          <div className="mb-1 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary">
            Recent runs
          </div>
          {scored.slice(0, 8).map((r) => (
            <div
              key={r.id}
              className="flex items-center gap-3 rounded border border-edge-subtle px-2.5 py-1.5 text-caption"
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
    </div>
  );
}
