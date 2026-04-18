import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WritePreviewCard } from './write-preview-card';
import type { TargetCandidate } from '../target-picker';

const TARGETS: TargetCandidate[] = [
  {
    kind: 'email_address',
    id: 'mrinal@a.com',
    label: 'Mrinal Raj',
    sub_label: 'mrinal@a.com',
    context: null,
  },
  {
    kind: 'email_address',
    id: 'mrinal@b.com',
    label: 'Mrinal Patel',
    sub_label: 'mrinal@b.com',
    context: null,
  },
];

describe('WritePreviewCard', () => {
  it('renders the title', () => {
    render(
      <WritePreviewCard
        title="Gmail · Send draft"
        onConfirm={() => {}}
        onCancel={() => {}}
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByText('Gmail · Send draft')).toBeInTheDocument();
  });

  it('renders meta rows when provided', () => {
    render(
      <WritePreviewCard
        title="Gmail · Send"
        meta={[
          { label: 'To', value: 'a@b.com, c@d.com' },
          { label: 'Subj', value: 'Q3' },
        ]}
        onConfirm={() => {}}
        onCancel={() => {}}
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByText('To')).toBeInTheDocument();
    expect(screen.getByText('a@b.com, c@d.com')).toBeInTheDocument();
    expect(screen.getByText('Subj')).toBeInTheDocument();
  });

  it('fires onConfirm when Confirm is clicked', async () => {
    const onConfirm = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={onConfirm} onCancel={() => {}}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('fires onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={() => {}} onCancel={onCancel}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('renders an Edit button when onEdit is provided', async () => {
    const onEdit = vi.fn();
    render(
      <WritePreviewCard title="x" onConfirm={() => {}} onCancel={() => {}} onEdit={onEdit}>
        body
      </WritePreviewCard>,
    );
    await userEvent.click(screen.getByRole('button', { name: /edit/i }));
    expect(onEdit).toHaveBeenCalled();
  });

  it('disables Confirm and shows the loading label when busy', () => {
    render(
      <WritePreviewCard
        title="x"
        onConfirm={() => {}}
        onCancel={() => {}}
        busy
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByRole('button', { name: /sending/i })).toBeDisabled();
  });

  it('renders TargetPicker when targetOptions has 2+ items', () => {
    const onChooseTarget = vi.fn();
    render(
      <WritePreviewCard
        title="Gmail · Send"
        onConfirm={() => {}}
        onCancel={() => {}}
        targetOptions={TARGETS}
        onChooseTarget={onChooseTarget}
      >
        body
      </WritePreviewCard>,
    );
    expect(screen.getByText(/Multiple candidates for Gmail · Send/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mrinal Raj/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mrinal Patel/ })).toBeInTheDocument();
    // Confirm/Cancel footer must be hidden while picking.
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
  });

  it('renders body when targetOptions has 0 or 1 item', () => {
    const { rerender } = render(
      <WritePreviewCard
        title="Gmail · Send"
        onConfirm={() => {}}
        onCancel={() => {}}
        targetOptions={[]}
      >
        body-empty
      </WritePreviewCard>,
    );
    expect(screen.getByText('body-empty')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();

    rerender(
      <WritePreviewCard
        title="Gmail · Send"
        onConfirm={() => {}}
        onCancel={() => {}}
        targetOptions={[TARGETS[0]]}
      >
        body-one
      </WritePreviewCard>,
    );
    expect(screen.getByText('body-one')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
  });
});
