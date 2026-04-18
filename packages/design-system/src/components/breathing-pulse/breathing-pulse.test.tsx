import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BreathingPulse } from './breathing-pulse';

describe('BreathingPulse', () => {
  it('renders an aria-hidden span with the breathe animation', () => {
    render(<BreathingPulse data-testid="p" />);
    const el = screen.getByTestId('p');
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute('aria-hidden', 'true');
    expect(el).toHaveClass('animate-breathe');
  });

  it('uses the agent-running tone by default', () => {
    render(<BreathingPulse data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('bg-agent-running');
  });

  it('honors the tone prop', () => {
    render(<BreathingPulse tone="awaiting" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('bg-agent-awaiting');
  });

  it('honors the size prop', () => {
    const { rerender } = render(<BreathingPulse size="sm" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('h-1.5');
    rerender(<BreathingPulse size="lg" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('h-3');
  });

  it('forwards className', () => {
    render(<BreathingPulse className="my-class" data-testid="p" />);
    expect(screen.getByTestId('p')).toHaveClass('my-class');
  });
});
