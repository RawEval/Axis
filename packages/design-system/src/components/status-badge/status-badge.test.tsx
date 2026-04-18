import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from './status-badge';

describe('StatusBadge', () => {
  it('renders the status text uppercased', () => {
    render(<StatusBadge status="running" />);
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
  });

  it('uses the agent-running tone color', () => {
    render(<StatusBadge status="running" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('text-agent-running');
  });

  it('renders a pulsing dot when pulse is true', () => {
    render(<StatusBadge status="thinking" pulse data-testid="s" />);
    const dot = screen.getByTestId('s').querySelector('span[aria-hidden="true"]');
    expect(dot).toBeInTheDocument();
    expect(dot).toHaveClass('animate-breathe');
  });

  it('renders a static dot when pulse is false', () => {
    render(<StatusBadge status="done" data-testid="s" />);
    const dot = screen.getByTestId('s').querySelector('span[aria-hidden="true"]');
    expect(dot).not.toHaveClass('animate-breathe');
  });

  it('exposes a className override', () => {
    render(<StatusBadge status="awaiting" className="my" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('my');
  });
});
