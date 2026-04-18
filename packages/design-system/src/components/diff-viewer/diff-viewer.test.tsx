import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiffViewer } from './diff-viewer';

describe('DiffViewer', () => {
  it('renders one row per line with a + / − /   prefix', () => {
    render(
      <DiffViewer
        lines={[
          { type: 'add', text: 'hello' },
          { type: 'del', text: 'gone' },
          { type: 'eq', text: 'same' },
        ]}
      />,
    );
    expect(screen.getByText('hello')).toBeInTheDocument();
    expect(screen.getByText('gone')).toBeInTheDocument();
    expect(screen.getByText('same')).toBeInTheDocument();
  });

  it('marks added lines with the success tone', () => {
    render(<DiffViewer lines={[{ type: 'add', text: 'x' }]} />);
    const row = screen.getByText('x').closest('div');
    expect(row).toHaveClass('text-success');
    expect(row).toHaveClass('bg-success/10');
  });

  it('marks removed lines with the danger tone and strikethrough', () => {
    render(<DiffViewer lines={[{ type: 'del', text: 'x' }]} />);
    const row = screen.getByText('x').closest('div');
    expect(row).toHaveClass('text-danger');
    expect(row).toHaveClass('bg-danger/10');
    expect(row).toHaveClass('line-through');
  });

  it('renders an optional header above the diff', () => {
    render(
      <DiffViewer
        header="notion://pages/q3"
        lines={[{ type: 'eq', text: 'x' }]}
      />,
    );
    expect(screen.getByText('notion://pages/q3')).toBeInTheDocument();
  });
});
