'use client';

import { Badge, SegmentedControl } from '@axis/design-system';
import {
  CAPABILITIES,
  capabilities,
  useCapabilities,
  type CapabilityId,
  type TrustMode,
} from '@/lib/capabilities';

const TIER_LABEL: Record<0 | 1 | 2, string> = {
  0: 'Read',
  1: 'Reversible',
  2: 'Irreversible',
};

const TIER_TONE: Record<0 | 1 | 2, 'success' | 'info' | 'warning'> = {
  0: 'success',
  1: 'info',
  2: 'warning',
};

const TRUST_OPTIONS: ReadonlyArray<{ value: TrustMode; label: string }> = [
  { value: 'ask',             label: 'Ask' },
  { value: 'auto-reversible', label: 'Auto if reversible' },
  { value: 'auto',            label: 'Auto' },
];

export function CapabilitiesPanel() {
  const modes = useCapabilities();

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h2 className="font-display text-heading-1 text-ink">What Axis can do</h2>
        <p className="text-body-s text-ink-secondary">
          Tier-2 (irreversible) capabilities always ask, regardless of trust mode.
        </p>
      </header>

      <ul className="divide-y divide-edge-subtle border-y border-edge-subtle">
        {CAPABILITIES.map((cap) => {
          const mode = modes[cap.id];
          const isIrreversible = cap.tier === 2;
          return (
            <li key={cap.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:gap-6">
              <div className="flex-1 min-w-0 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-body-s font-medium text-ink">{cap.label}</span>
                  <Badge tone={TIER_TONE[cap.tier]}>{TIER_LABEL[cap.tier]}</Badge>
                </div>
                <div className="font-mono text-mono-s text-ink-tertiary">{cap.id}</div>
                <p className="text-caption text-ink-secondary">{cap.description}</p>
              </div>
              <SegmentedControl
                value={isIrreversible ? 'ask' : mode}
                onChange={(next: TrustMode) => {
                  if (!isIrreversible) capabilities.setMode(cap.id as CapabilityId, next);
                }}
                options={TRUST_OPTIONS}
              />
            </li>
          );
        })}
      </ul>
    </div>
  );
}
