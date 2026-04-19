import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ConnectorFreshnessChip } from './connector-freshness-chip';

describe('ConnectorFreshnessChip', () => {
  it('renders green text when last_status=ok and synced recently', () => {
    render(
      <ConnectorFreshnessChip
        source="notion"
        state={{
          source: 'notion',
          last_synced_at: new Date().toISOString(),
          last_status: 'ok',
          last_error: null,
        }}
      />,
    );
    const chip = screen.getByText(/synced/i);
    expect(chip.className).toMatch(/emerald/);
  });

  it('renders amber when last_synced_at is older than 2 minutes', () => {
    const old = new Date(Date.now() - 5 * 60_000).toISOString();
    render(
      <ConnectorFreshnessChip
        source="notion"
        state={{
          source: 'notion',
          last_synced_at: old,
          last_status: 'ok',
          last_error: null,
        }}
      />,
    );
    const chip = screen.getByText(/synced/i);
    expect(chip.className).toMatch(/amber/);
  });

  it('renders red Reconnect button when last_status=auth_failed', () => {
    const onReconnect = vi.fn();
    render(
      <ConnectorFreshnessChip
        source="notion"
        state={{
          source: 'notion',
          last_synced_at: null,
          last_status: 'auth_failed',
          last_error: 'token expired',
        }}
        onReconnect={onReconnect}
      />,
    );
    const btn = screen.getByRole('button', { name: /reconnect notion/i });
    expect(btn.className).toMatch(/red/);
    btn.click();
    expect(onReconnect).toHaveBeenCalled();
  });
});
