import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './badge';

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>12</Badge>);
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('defaults to neutral tone', () => {
    render(<Badge data-testid="b">x</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('bg-canvas-elevated');
  });

  it('applies the success tone', () => {
    render(<Badge tone="success" data-testid="b">ok</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('text-success');
  });

  it('applies the danger tone', () => {
    render(<Badge tone="danger" data-testid="b">err</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('text-danger');
  });

  it('renders the with-dot variant', () => {
    render(<Badge tone="warning" dot data-testid="b">stale</Badge>);
    const el = screen.getByTestId('b');
    expect(el.querySelector('span[aria-hidden="true"]')).toBeInTheDocument();
  });

  it('forwards className', () => {
    render(<Badge className="my-class" data-testid="b">x</Badge>);
    expect(screen.getByTestId('b')).toHaveClass('my-class');
  });
});
