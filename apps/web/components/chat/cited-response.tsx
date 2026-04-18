'use client';

import clsx from 'clsx';
import { useState } from 'react';

/** One citation span in the text (character offsets into `content`). */
export type CitationSpan = {
  start: number;
  end: number;
  label?: string | null;
};

/** One cited source referenced by an assistant message. */
export type Citation = {
  id?: string | null;
  source_type: string;        // notion_page | slack_message | gmail_thread | ...
  provider?: string | null;   // notion | slack | gmail | ...
  ref_id?: string | null;
  url?: string | null;
  title?: string | null;
  actor?: string | null;
  excerpt?: string | null;
  occurred_at?: string | null;
  spans?: CitationSpan[];
};

/**
 * Renders an assistant message with highlighted citation spans inline and
 * a "Sources" list below. Hovering a highlight scrolls its matching source
 * card into view and emphasizes it; clicking it opens the source URL.
 */
export function CitedResponse({
  content,
  citations,
}: {
  content: string;
  citations: Citation[];
}) {
  const [hoveredCitationId, setHoveredCitationId] = useState<string | null>(null);

  // Build an ordered list of all spans with their owning citation
  const hits: Array<{ start: number; end: number; citation: Citation; label?: string | null }> = [];
  citations.forEach((c) => {
    (c.spans ?? []).forEach((span) => {
      hits.push({ start: span.start, end: span.end, citation: c, label: span.label });
    });
  });
  hits.sort((a, b) => a.start - b.start);

  // Split the content into plain and highlighted segments
  const segments: Array<
    | { kind: 'text'; text: string }
    | { kind: 'highlight'; text: string; citation: Citation }
  > = [];
  let cursor = 0;
  hits.forEach((hit) => {
    if (hit.start < cursor) return; // overlapping; skip the inner ones
    if (hit.start > cursor) {
      segments.push({ kind: 'text', text: content.slice(cursor, hit.start) });
    }
    segments.push({
      kind: 'highlight',
      text: content.slice(hit.start, hit.end),
      citation: hit.citation,
    });
    cursor = hit.end;
  });
  if (cursor < content.length) {
    segments.push({ kind: 'text', text: content.slice(cursor) });
  }

  return (
    <div className="space-y-4">
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
        {segments.length === 0 ? (
          <span>{content}</span>
        ) : (
          segments.map((seg, i) => {
            if (seg.kind === 'text') return <span key={i}>{seg.text}</span>;
            const cid = seg.citation.id ?? seg.citation.ref_id ?? `${i}`;
            const active = hoveredCitationId === cid;
            return (
              <mark
                key={i}
                className={clsx(
                  'cursor-pointer rounded px-0.5 transition-colors',
                  active
                    ? 'bg-brand-200 text-brand-700'
                    : 'bg-brand-50 text-brand-700 hover:bg-brand-100',
                )}
                onMouseEnter={() => setHoveredCitationId(cid)}
                onMouseLeave={() => setHoveredCitationId(null)}
                onClick={() => {
                  if (seg.citation.url && typeof window !== 'undefined') {
                    window.open(seg.citation.url, '_blank', 'noopener,noreferrer');
                  }
                }}
              >
                {seg.text}
              </mark>
            );
          })
        )}
      </div>

      {citations.length > 0 && (
        <div className="border-t border-edge-subtle pt-3">
          <div className="label-caps mb-2">
            Sources · {citations.length}
          </div>
          <ul className="space-y-2">
            {citations.map((c, i) => {
              const cid = c.id ?? c.ref_id ?? `${i}`;
              const active = hoveredCitationId === cid;
              return (
                <li
                  key={cid}
                  onMouseEnter={() => setHoveredCitationId(cid)}
                  onMouseLeave={() => setHoveredCitationId(null)}
                  className={clsx(
                    'rounded border px-3 py-2 transition-colors',
                    active
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-edge bg-canvas-raised',
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        {c.provider && (
                          <span className="label-caps">{c.provider}</span>
                        )}
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="truncate text-sm font-medium text-brand-700 hover:underline"
                          >
                            {c.title || c.url}
                          </a>
                        ) : (
                          <span className="truncate text-sm font-medium text-ink">
                            {c.title || c.source_type}
                          </span>
                        )}
                      </div>
                      {c.actor && (
                        <div className="mt-0.5 text-xs text-ink-tertiary">
                          {c.actor}
                        </div>
                      )}
                      {c.excerpt && (
                        <p className="mt-1 line-clamp-2 text-xs text-ink-secondary">
                          {c.excerpt}
                        </p>
                      )}
                    </div>
                    {c.occurred_at && (
                      <div className="whitespace-nowrap text-[11px] text-ink-tertiary">
                        {new Date(c.occurred_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
