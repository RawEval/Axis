'use client';

import { useState } from 'react';
import {
  Badge,
  Button,
  EmptyState,
  PageHeader,
  Panel,
  PanelBody,
  PanelHeader,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from '@/components/ui';
import {
  useDeleteEpisodic,
  useMemorySearch,
  useMemoryStats,
  type MemoryRow,
} from '@/lib/queries/memory';

const TIERS: Array<{ value: string | null; label: string }> = [
  { value: null, label: 'all tiers' },
  { value: 'episodic', label: 'episodic' },
  { value: 'semantic', label: 'semantic' },
  { value: 'procedural', label: 'procedural' },
];

export default function MemoryPage() {
  const [query, setQuery] = useState('');
  const [tier, setTier] = useState<string | null>(null);
  const stats = useMemoryStats();
  const search = useMemorySearch(query.trim() || 'recent', tier);
  const del = useDeleteEpisodic();

  const rows = search.data ?? [];

  return (
    <div className="mx-auto flex min-h-full max-w-6xl flex-col gap-5 px-6 py-6">
      <PageHeader title="Memory" />

      <Panel>
        <PanelHeader>
          <div className="text-sm font-semibold text-ink">Overview</div>
          <Badge tone="brand">
            {stats.data?.embedding_provider ?? 'loading'}
          </Badge>
        </PanelHeader>
        <PanelBody>
          <dl className="grid grid-cols-1 gap-y-3 sm:grid-cols-3">
            <dt className="label-caps">Episodic rows</dt>
            <dd className="col-span-2 text-sm text-ink">
              {stats.data?.episodic_count ?? '—'}
            </dd>
            <dt className="label-caps">Semantic entities</dt>
            <dd className="col-span-2 text-sm text-ink">
              {stats.data?.semantic_count ?? '—'}
            </dd>
            <dt className="label-caps">Embedding provider</dt>
            <dd className="col-span-2 text-sm text-ink-secondary">
              {stats.data?.embedding_provider ?? '—'}
            </dd>
          </dl>
        </PanelBody>
      </Panel>

      <Panel>
        <PanelHeader>
          <div className="text-sm font-semibold text-ink">Search</div>
          <div className="flex flex-wrap gap-1.5">
            {TIERS.map((t) => (
              <Button
                key={t.label}
                size="sm"
                variant={tier === t.value ? 'primary' : 'secondary'}
                onClick={() => setTier(t.value)}
              >
                {t.label}
              </Button>
            ))}
          </div>
        </PanelHeader>
        <PanelBody>
          <div className="mb-3 flex gap-2">
            <input
              type="text"
              placeholder="search your memory — e.g. 'Q3 planning'"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 rounded border border-canvas-subtle bg-canvas px-3 py-1.5 text-sm text-ink outline-none focus:border-brand"
            />
          </div>

          {search.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-6 animate-pulse rounded bg-canvas-subtle"
                />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <EmptyState
              title="No memories match"
              description={
                stats.data && stats.data.episodic_count === 0
                  ? "Memory is empty. Ask Axis a question — every turn gets stored as an episodic memory automatically."
                  : 'Try a broader query or switch tiers.'
              }
            />
          ) : (
            <Table>
              <THead>
                <tr>
                  <TH>Tier</TH>
                  <TH>Type</TH>
                  <TH>Content</TH>
                  <TH>Score</TH>
                  <TH className="text-right">Actions</TH>
                </tr>
              </THead>
              <TBody>
                {rows.map((row) => (
                  <MemoryRowComponent
                    key={`${row.tier}:${row.id}`}
                    row={row}
                    onDelete={
                      row.tier === 'episodic'
                        ? () => del.mutate(row.id)
                        : undefined
                    }
                  />
                ))}
              </TBody>
            </Table>
          )}
        </PanelBody>
      </Panel>
    </div>
  );
}

function MemoryRowComponent({
  row,
  onDelete,
}: {
  row: MemoryRow;
  onDelete?: () => void;
}) {
  const tone =
    row.tier === 'episodic'
      ? 'brand'
      : row.tier === 'semantic'
        ? 'info'
        : 'neutral';
  return (
    <TR>
      <TD>
        <Badge tone={tone} dot>
          {row.tier}
        </Badge>
      </TD>
      <TD className="text-ink-secondary">{row.type}</TD>
      <TD className="font-medium text-ink">
        <div className="max-w-xl truncate">{row.content}</div>
      </TD>
      <TD className="text-ink-tertiary">{row.score.toFixed(3)}</TD>
      <TD className="text-right">
        {onDelete && (
          <Button size="sm" variant="ghost" onClick={onDelete}>
            Delete
          </Button>
        )}
      </TD>
    </TR>
  );
}
