'use client';

import { useState } from 'react';
import {
  Activity as ActivityIcon,
  FileText,
  GitBranch,
  Mail,
  MessageSquare,
} from 'lucide-react';
import {
  Badge,
  Button,
  Card,
  CardBody,
  SegmentedControl,
  Skeleton,
} from '@axis/design-system';
import { useActivity, type ActivityEvent } from '@/lib/queries/activity';
import { useFeed, useSurfaceAction, type ProactiveSurface } from '@/lib/queries/feed';

type FilterValue = 'all' | 'approvals' | 'writes' | 'errors' | 'proactive';

const FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'approvals', label: 'Approvals' },
  { value: 'writes', label: 'Writes' },
  { value: 'errors', label: 'Errors' },
  { value: 'proactive', label: 'Proactive' },
] as const;

const SOURCE_ICONS: Record<string, typeof ActivityIcon> = {
  slack: MessageSquare,
  notion: FileText,
  gmail: Mail,
  gdrive: FileText,
  github: GitBranch,
};

function confidenceTone(score: number | null): 'warning' | 'neutral' | 'success' {
  if (score == null) return 'neutral';
  if (score >= 0.75) return 'success';
  if (score >= 0.5) return 'neutral';
  return 'warning';
}

function confidenceLabel(score: number | null): string {
  if (score == null) return 'MED';
  if (score >= 0.75) return 'HIGH';
  if (score >= 0.5) return 'MED';
  return 'LOW';
}

function formatTimestamp(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function FeedPage() {
  const { data: surfaces, isLoading: surfacesLoading } = useFeed();
  const { data: events, isLoading: eventsLoading } = useActivity();
  const action = useSurfaceAction();
  const [filter, setFilter] = useState<FilterValue>('all');

  const hasSurfaces = surfaces && surfaces.length > 0;
  const hasEvents = events && events.length > 0;
  const loading = surfacesLoading || eventsLoading;

  const showSurfaces = filter === 'all' || filter === 'proactive' || filter === 'approvals';
  const showEvents = filter === 'all' || filter === 'writes' || filter === 'errors';

  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-8 px-6 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Activity</h1>
        <p className="text-body text-ink-secondary">
          Everything Axis has done — and everything that needs your attention.
        </p>
      </header>

      <SegmentedControl
        value={filter}
        onChange={(v) => setFilter(v as FilterValue)}
        options={FILTER_OPTIONS}
        aria-label="Filter activity"
      />

      {showSurfaces && hasSurfaces && (
        <section aria-labelledby="needs-attention">
          <h2
            id="needs-attention"
            className="mb-3 flex items-baseline gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
          >
            <span>Needs your attention</span>
            <span className="text-ink-secondary tabular-nums">({surfaces.length})</span>
          </h2>
          <div className="flex flex-col gap-3">
            {surfaces.map((s) => (
              <SurfaceCard key={s.id} surface={s} onAction={action.mutate} />
            ))}
          </div>
        </section>
      )}

      {showEvents && (
        <section aria-labelledby="recent-activity">
          <h2
            id="recent-activity"
            className="mb-3 flex items-baseline gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
          >
            <span>Recent activity</span>
            <span className="text-ink-secondary tabular-nums">({events?.length ?? 0})</span>
          </h2>
          {loading ? (
            <div className="flex flex-col gap-2">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14" />
              ))}
            </div>
          ) : !hasEvents ? (
            <div className="flex flex-col items-center justify-center gap-4 py-16 border border-dashed border-edge-subtle rounded-lg">
              <ActivityIcon size={28} className="text-ink-tertiary" aria-hidden="true" />
              <div className="text-center space-y-1">
                <p className="font-display text-heading-2 text-ink">No activity yet</p>
                <p className="text-body-s text-ink-tertiary">
                  Connect a tool and the activity stream will populate here.
                </p>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => (window.location.href = '/connections')}
              >
                Connect a tool
              </Button>
            </div>
          ) : (
            <div className="overflow-hidden rounded-lg border border-edge-subtle">
              {events.map((ev) => (
                <EventRow key={ev.id} event={ev} />
              ))}
            </div>
          )}
        </section>
      )}
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
  return (
    <Card>
      <CardBody className="flex items-start gap-4">
        <ActivityIcon size={16} className="mt-1 text-ink-tertiary" aria-hidden="true" />
        <div className="flex-1 min-w-0 space-y-1">
          <div className="text-body font-medium text-ink">{surface.title}</div>
          {surface.context_snippet && (
            <div className="text-body-s text-ink-secondary truncate">
              {surface.context_snippet}
            </div>
          )}
          <div className="flex items-center gap-2 pt-1">
            <Badge tone="neutral">{surface.signal_type.replaceAll('_', ' ')}</Badge>
            <Badge tone={confidenceTone(surface.confidence_score)}>
              {confidenceLabel(surface.confidence_score)}
            </Badge>
            <span className="font-mono text-mono-s text-ink-tertiary tabular-nums">
              {formatTimestamp(surface.created_at)}
            </span>
          </div>
        </div>
        <div className="flex flex-shrink-0 gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onAction({ id: surface.id, action: 'dismiss' })}
          >
            Dismiss
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={() => onAction({ id: surface.id, action: 'accept' })}
          >
            Act on it
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}

function EventRow({ event }: { event: ActivityEvent }) {
  const Icon = SOURCE_ICONS[event.source] ?? ActivityIcon;
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-edge-subtle last:border-b-0 hover:bg-canvas-elevated transition-colors">
      <Icon size={16} className="text-ink-tertiary flex-shrink-0" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <div className="text-body-s text-ink truncate">{event.title}</div>
        {event.snippet && (
          <div className="mt-0.5 truncate text-caption text-ink-tertiary">{event.snippet}</div>
        )}
      </div>
      <div className="flex flex-shrink-0 flex-col items-end gap-0.5">
        {event.actor && (
          <span className="text-caption text-ink-secondary">{event.actor}</span>
        )}
        <span className="font-mono text-mono-s text-ink-tertiary tabular-nums">
          {formatTimestamp(event.occurred_at)}
        </span>
      </div>
    </div>
  );
}
