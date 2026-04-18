import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WritePreviewCard } from './write-preview-card';

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
});
