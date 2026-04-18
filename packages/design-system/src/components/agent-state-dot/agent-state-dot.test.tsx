import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AgentStateDot } from './agent-state-dot';

describe('AgentStateDot', () => {
  it('renders with the agent-running tone for the running state', () => {
    render(<AgentStateDot state="running" data-testid="d" />);
    const el = screen.getByTestId('d');
    const dot = el.querySelector('span[aria-hidden="true"]');
    expect(dot).toHaveClass('bg-agent-running');
  });

  it('uses the awaiting tone with pulse for the awaiting state', () => {
    render(<AgentStateDot state="awaiting" data-testid="d" />);
    const dot = screen.getByTestId('d').querySelector('span[aria-hidden="true"]');
    expect(dot).toHaveClass('bg-agent-awaiting');
    expect(dot).toHaveClass('animate-breathe');
  });

  it('does not pulse for the recovered state', () => {
    render(<AgentStateDot state="recovered" data-testid="d" />);
    const dot = screen.getByTestId('d').querySelector('span[aria-hidden="true"]');
    expect(dot).not.toHaveClass('animate-breathe');
  });

  it('renders an sr-only label describing the state', () => {
    render(<AgentStateDot state="blocked" />);
    expect(screen.getByText('Blocked', { selector: '.sr-only' })).toBeInTheDocument();
  });

  it('honors a custom label', () => {
    render(<AgentStateDot state="running" label="Drafting reply" />);
    expect(screen.getByText('Drafting reply', { selector: '.sr-only' })).toBeInTheDocument();
  });

  it('forwards className', () => {
    render(<AgentStateDot state="running" className="my-class" data-testid="d" />);
    expect(screen.getByTestId('d')).toHaveClass('my-class');
  });
});
