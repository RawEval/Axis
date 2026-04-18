import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CitationChip } from './citation-chip';

describe('CitationChip', () => {
  it('renders the index inside square brackets', () => {
    render(<CitationChip index={3} sourceId="s_3" />);
    expect(screen.getByText('[3]')).toBeInTheDocument();
  });

  it('exposes the source title via aria-label when provided', () => {
    render(<CitationChip index={1} sourceId="s_1" sourceTitle="Q3 Roadmap" />);
    expect(screen.getByRole('button')).toHaveAccessibleName('Source 1: Q3 Roadmap');
  });

  it('falls back to a generic aria-label', () => {
    render(<CitationChip index={1} sourceId="s_1" />);
    expect(screen.getByRole('button')).toHaveAccessibleName('Source 1');
  });

  it('fires onClick with the sourceId', async () => {
    const onClick = vi.fn();
    render(<CitationChip index={2} sourceId="s_42" onClick={onClick} />);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledWith('s_42');
  });

  it('renders inside a sup element', () => {
    render(<CitationChip index={1} sourceId="s_1" data-testid="c" />);
    expect(screen.getByTestId('c').tagName).toBe('SUP');
  });
});
