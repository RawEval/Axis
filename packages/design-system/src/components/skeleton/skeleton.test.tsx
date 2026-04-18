import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from './skeleton';

describe('Skeleton', () => {
  it('renders an empty container with shimmer animation', () => {
    render(<Skeleton data-testid="s" />);
    const el = screen.getByTestId('s');
    expect(el).toBeInTheDocument();
    expect(el).toHaveClass('animate-shimmer');
  });

  it('respects width and height props', () => {
    render(<Skeleton width={120} height={20} data-testid="s" />);
    const el = screen.getByTestId('s');
    expect(el).toHaveStyle({ width: '120px', height: '20px' });
  });

  it('exposes className override', () => {
    render(<Skeleton className="my" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('my');
  });

  it('uses the rounded variant when rounded="full"', () => {
    render(<Skeleton rounded="full" data-testid="s" />);
    expect(screen.getByTestId('s')).toHaveClass('rounded-full');
  });
});
