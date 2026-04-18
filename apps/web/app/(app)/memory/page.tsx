'use client';

import { useMemo, useState } from 'react';
import {
  Circle,
  Diamond,
  ExternalLink,
  Pin,
  Plus,
  Search,
  Trash2,
} from 'lucide-react';
import {
  Badge,
  Button,
  Input,
  Modal,
  ModalBody,
  ModalDescription,
  ModalFooter,
  ModalTitle,
  Skeleton,
} from '@axis/design-system';
import {
  useDeleteEpisodic,
  useMemorySearch,
  useMemoryStats,
  type MemoryRow,
} from '@/lib/queries/memory';

type Tier = 'pinned' | 'episodic' | 'semantic';

const TIER_META: Record<Tier, { label: string; icon: typeof Pin }> = {
  pinned: { label: 'Pinned', icon: Pin },
  episodic: { label: 'Episodic', icon: Circle },
  semantic: { label: 'Semantic', icon: Diamond },
};

function isPinned(row: MemoryRow): boolean {
  const pinned = (row.metadata as Record<string, unknown> | null)?.pinned;
  return pinned === true;
}

export default function MemoryPage() {
  const [query, setQuery] = useState('');
  const [bulkClearOpen, setBulkClearOpen] = useState(false);
  const stats = useMemoryStats();
  const search = useMemorySearch(query.trim() || 'recent', null);
  const del = useDeleteEpisodic();

  const rows = search.data ?? [];

  const grouped = useMemo(() => {
    const buckets: Record<Tier, MemoryRow[]> = {
      pinned: [],
      episodic: [],
      semantic: [],
    };
    for (const r of rows) {
      if (isPinned(r)) buckets.pinned.push(r);
      else if (r.tier === 'episodic') buckets.episodic.push(r);
      else if (r.tier === 'semantic') buckets.semantic.push(r);
      else buckets.episodic.push(r);
    }
    return buckets;
  }, [rows]);

  const totalEpisodic = stats.data?.episodic_count ?? 0;
  const totalSemantic = stats.data?.semantic_count ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-10 px-12 py-10">
      <header className="space-y-2">
        <h1 className="font-display text-display-l text-ink">Memory</h1>
        <p className="text-body text-ink-secondary">
          What Axis remembers about you, your work, and your tools.
        </p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search
            size={14}
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-tertiary"
          />
          <Input
            placeholder="Search memory — e.g. 'Q3 planning'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button variant="primary" size="sm" leadingIcon={<Plus size={14} aria-hidden="true" />}>
          Add memory
        </Button>
        <button
          type="button"
          onClick={() => setBulkClearOpen(true)}
          className="text-body-s text-ink-tertiary hover:text-danger transition-colors"
        >
          Bulk clear…
        </button>
      </div>

      <MemorySection
        tier="pinned"
        rows={grouped.pinned}
        count={grouped.pinned.length}
        loading={search.isLoading}
        onDelete={undefined}
      />

      <MemorySection
        tier="episodic"
        rows={grouped.episodic}
        count={totalEpisodic || grouped.episodic.length}
        loading={search.isLoading}
        onDelete={(id) => del.mutate(id)}
      />

      <MemorySection
        tier="semantic"
        rows={grouped.semantic}
        count={totalSemantic || grouped.semantic.length}
        loading={search.isLoading}
        onDelete={undefined}
      />

      <BulkClearModal
        open={bulkClearOpen}
        onOpenChange={setBulkClearOpen}
        episodicCount={totalEpisodic}
      />
    </div>
  );
}

function MemorySection({
  tier,
  rows,
  count,
  loading,
  onDelete,
}: {
  tier: Tier;
  rows: MemoryRow[];
  count: number;
  loading: boolean;
  onDelete?: (id: string) => void;
}) {
  const meta = TIER_META[tier];
  const Icon = meta.icon;
  return (
    <section aria-labelledby={`memory-${tier}`}>
      <h2
        id={`memory-${tier}`}
        className="mb-3 flex items-baseline gap-2 font-mono text-[11px] uppercase tracking-[0.08em] text-ink-tertiary"
      >
        <span>{meta.label}</span>
        <span className="text-ink-secondary tabular-nums">· {count}</span>
      </h2>

      {loading ? (
        <div className="flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-edge-subtle px-4 py-6 text-center">
          <p className="text-body-s text-ink-tertiary">
            {tier === 'pinned'
              ? 'Nothing pinned yet. Pin a memory to keep it always available.'
              : `No ${meta.label.toLowerCase()} memories.`}
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-edge-subtle">
          {rows.map((row) => (
            <MemoryRowItem
              key={`${row.tier}:${row.id}`}
              row={row}
              icon={Icon}
              onDelete={onDelete ? () => onDelete(row.id) : undefined}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function MemoryRowItem({
  row,
  icon: Icon,
  onDelete,
}: {
  row: MemoryRow;
  icon: typeof Pin;
  onDelete?: () => void;
}) {
  const sourceUrl =
    typeof (row.metadata as Record<string, unknown>)?.source_url === 'string'
      ? ((row.metadata as Record<string, unknown>).source_url as string)
      : null;

  return (
    <div className="group flex items-center gap-3 px-4 py-3 border-b border-edge-subtle last:border-b-0 hover:bg-canvas-elevated transition-colors">
      <Icon size={14} className="text-ink-tertiary flex-shrink-0" aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <div className="text-body-s text-ink truncate">{row.content}</div>
        <div className="mt-0.5 flex items-center gap-2 text-caption text-ink-tertiary">
          <span>{row.type}</span>
          <span aria-hidden="true">·</span>
          <span className="font-mono tabular-nums">{row.score.toFixed(3)}</span>
        </div>
      </div>
      <Badge tone="neutral">{row.tier}</Badge>
      <div className="flex flex-shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {sourceUrl && (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-surface"
            aria-label="View source"
          >
            <ExternalLink size={14} aria-hidden="true" />
          </a>
        )}
        <button
          type="button"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-surface"
          aria-label="Pin"
        >
          <Pin size={14} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-tertiary hover:text-ink hover:bg-canvas-surface"
          aria-label="Promote"
        >
          <Diamond size={14} aria-hidden="true" />
        </button>
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-ink-tertiary hover:text-danger hover:bg-canvas-surface"
            aria-label="Forget"
          >
            <Trash2 size={14} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}

function BulkClearModal({
  open,
  onOpenChange,
  episodicCount,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  episodicCount: number;
}) {
  return (
    <Modal open={open} onOpenChange={onOpenChange}>
      <ModalTitle>Clear memory?</ModalTitle>
      <ModalDescription>
        This permanently removes {episodicCount} episodic memories. Pinned and semantic
        memories are kept. This cannot be undone.
      </ModalDescription>
      <ModalBody>
        <p className="text-body-s text-ink-secondary">
          To bulk-clear memory, contact support — this protected action is not yet
          self-serve in the UI.
        </p>
      </ModalBody>
      <ModalFooter>
        <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button variant="danger" size="sm" disabled>
          Clear all
        </Button>
      </ModalFooter>
    </Modal>
  );
}
