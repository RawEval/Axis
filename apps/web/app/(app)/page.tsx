'use client';

import Link from 'next/link';
import { ArrowRight, MessageSquare, Plug } from 'lucide-react';
import {
  BreathingPulse,
  Card,
  CardBody,
} from '@axis/design-system';
import { useConnectors } from '@/lib/queries/connectors';
import { OnboardingBanner } from '@/components/home/onboarding-banner';

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

const SUGGESTED_PROMPTS: ReadonlyArray<string> = [
  'Summarize what happened in #product on Slack today',
  'Draft a Q3 retro in Notion',
  'Triage my Gmail inbox',
];

const LINK_BUTTON_CLASSES =
  'inline-flex items-center gap-2 h-8 px-3 rounded-md text-body-s text-ink-secondary hover:text-ink hover:bg-canvas-elevated transition-colors';

export default function HomePage() {
  const { data: connectors } = useConnectors();

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header>
        <h1 className="font-display text-display-l text-ink">{greeting()}</h1>
      </header>

      <OnboardingBanner />

      <section aria-labelledby="running-now">
        <SectionHeader id="running-now" title="Running now" count={0} />
        <Card>
          <CardBody className="flex items-center justify-between py-6">
            <div className="flex items-center gap-3 text-ink-secondary">
              <BreathingPulse tone="background" size="sm" />
              <span className="text-body-s">Nothing running yet.</span>
            </div>
            <Link href="/chat" className={LINK_BUTTON_CLASSES}>
              <MessageSquare size={14} aria-hidden="true" />
              Start a chat
              <ArrowRight size={14} aria-hidden="true" />
            </Link>
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="needs-approval">
        <SectionHeader id="needs-approval" title="Needs your approval" count={0} />
        <Card>
          <CardBody className="py-6 text-body-s text-ink-secondary">
            No actions waiting on you.
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="connectors">
        <SectionHeader id="connectors" title="Connectors" count={connectors?.length ?? 0} />
        <Card>
          <CardBody className="flex items-center justify-between py-5">
            <div className="flex items-center gap-3">
              {(connectors ?? []).slice(0, 6).map((c) => (
                <span
                  key={c.tool}
                  title={c.tool}
                  className={`inline-block h-2 w-2 rounded-full ${
                    c.status === 'connected' ? 'bg-success' :
                    c.status === 'error' ? 'bg-danger' :
                    'bg-canvas-elevated border border-edge'
                  }`}
                />
              ))}
              {(!connectors || connectors.length === 0) && (
                <span className="text-body-s text-ink-tertiary">No connectors yet.</span>
              )}
            </div>
            <Link href="/connections" className={LINK_BUTTON_CLASSES}>
              <Plug size={14} aria-hidden="true" />
              Manage
            </Link>
          </CardBody>
        </Card>
      </section>

      <section aria-labelledby="suggested">
        <SectionHeader id="suggested" title="Suggested prompts" count={SUGGESTED_PROMPTS.length} />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <Link
              key={prompt}
              href={`/chat?prompt=${encodeURIComponent(prompt)}`}
              className="block p-4 rounded-md border border-edge-subtle bg-canvas-surface hover:border-edge hover:bg-canvas-elevated transition-colors"
            >
              <span className="text-body-s text-ink">{prompt}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function SectionHeader({
  id,
  title,
  count,
}: {
  id: string;
  title: string;
  count: number;
}) {
  return (
    <h2
      id={id}
      className="mb-3 flex items-baseline gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
    >
      <span>{title}</span>
      <span className="text-ink-secondary tabular-nums">({count})</span>
    </h2>
  );
}
