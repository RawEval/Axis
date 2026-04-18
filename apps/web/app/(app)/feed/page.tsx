'use client';

import { Badge, Button, PageHeader } from '@/components/ui';
import { useActivity, type ActivityEvent } from '@/lib/queries/activity';
import { useFeed, useSurfaceAction, type ProactiveSurface } from '@/lib/queries/feed';

const SOURCE_COLORS: Record<string, string> = {
  slack: 'bg-[#4A154B]',
  notion: 'bg-[#000000]',
  gmail: 'bg-[#EA4335]',
  gdrive: 'bg-[#4285F4]',
  github: 'bg-[#24292e]',
};

export default function FeedPage() {
  const { data: surfaces, isLoading: surfacesLoading } = useFeed();
  const { data: events, isLoading: eventsLoading } = useActivity();
  const action = useSurfaceAction();

  const hasSurfaces = surfaces && surfaces.length > 0;
  const hasEvents = events && events.length > 0;
  const loading = surfacesLoading || eventsLoading;

  return (
    <div className="mx-auto flex min-h-full max-w-4xl flex-col gap-6 px-6 py-6">
      <PageHeader title="Activity" />

      {/* Proactive suggestions — attention-worthy items */}
      {hasSurfaces && (
        <section>
          <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-tertiary">
            Needs your attention
          </div>
          <div className="flex flex-col gap-2">
            {surfaces.map((s) => (
              <SurfaceCard key={s.id} surface={s} onAction={action.mutate} />
            ))}
          </div>
        </section>
      )}

      {/* Activity timeline */}
      <section>
        <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-tertiary">
          Recent activity
        </div>
        {loading ? (
          <div className="space-y-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg border border-edge bg-canvas-raised" />
            ))}
          </div>
        ) : !hasEvents ? (
          <div className="rounded-lg border border-edge bg-canvas-raised px-5 py-8 text-center">
            <div className="mb-1 text-sm font-medium text-ink">No activity yet</div>
            <div className="text-xs text-ink-tertiary">Connect a tool and the activity stream will populate here.</div>
            <Button variant="secondary" size="sm" className="mt-3" onClick={() => (window.location.href = '/connections')}>
              Connect a tool
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-1.5">
            {events.map((ev) => (
              <EventRow key={ev.id} event={ev} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function SurfaceCard({
  surface,
  onAction,
}: {
  surface: ProactiveSurface;
  onAction: (input: { id: string; action: 'accept' | 'dismiss' }) => void;
}) {
  const pct = surface.confidence_score != null ? `${Math.round(surface.confidence_score * 100)}%` : null;
  return (
    <div className="flex items-start gap-4 rounded-lg border border-warning/20 bg-warning-bg/20 px-4 py-3">
      <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md bg-warning text-xs text-white">!</div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-ink">{surface.title}</div>
        {surface.context_snippet && (
          <div className="mt-0.5 truncate text-xs text-ink-secondary">{surface.context_snippet}</div>
        )}
        <div className="mt-1.5 flex items-center gap-2">
          <Badge tone="neutral">{surface.signal_type.replaceAll('_', ' ')}</Badge>
          {pct && <span className="text-xs text-ink-tertiary">{pct} confidence</span>}
        </div>
      </div>
      <div className="flex flex-shrink-0 gap-1.5">
        <Button size="xs" variant="ghost" onClick={() => onAction({ id: surface.id, action: 'dismiss' })}>
          Dismiss
        </Button>
        <Button size="xs" variant="primary" onClick={() => onAction({ id: surface.id, action: 'accept' })}>
          Act on it
        </Button>
      </div>
    </div>
  );
}

function EventRow({ event }: { event: ActivityEvent }) {
  const sourceColor = SOURCE_COLORS[event.source] ?? 'bg-ink-disabled';
  return (
    <div className="flex items-center gap-3 rounded-lg border border-edge bg-canvas-raised px-4 py-3 transition-colors hover:bg-canvas-subtle">
      <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-[10px] font-bold text-white ${sourceColor}`}>
        {event.source.charAt(0).toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-ink">{event.title}</div>
        {event.snippet && (
          <div className="mt-0.5 truncate text-xs text-ink-tertiary">{event.snippet}</div>
        )}
      </div>
      <div className="flex flex-shrink-0 flex-col items-end gap-0.5">
        {event.actor && <span className="text-xs text-ink-secondary">{event.actor}</span>}
        <span className="text-[10px] text-ink-tertiary">
          {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : ''}
        </span>
      </div>
    </div>
  );
}
