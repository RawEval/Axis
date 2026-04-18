import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Avatar } from './avatar';

describe('Avatar', () => {
  it('renders the first letter of name when no src', () => {
    render(<Avatar name="Alice" />);
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('renders an img when src is provided', () => {
    render(<Avatar name="Alice" src="/x.png" />);
    expect(screen.getByRole('img')).toHaveAttribute('src', '/x.png');
  });

  it('uses the agent shape (squircle) when shape="agent"', () => {
    render(<Avatar name="Axis" shape="agent" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('rounded-md');
  });

  it('uses circle by default', () => {
    render(<Avatar name="x" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('rounded-full');
  });

  it('applies size sm/md/lg', () => {
    const { rerender } = render(<Avatar name="x" size="sm" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('h-6');
    rerender(<Avatar name="x" size="lg" data-testid="a" />);
    expect(screen.getByTestId('a')).toHaveClass('h-10');
  });

  it('falls back to ? when no name and no src', () => {
    render(<Avatar />);
    expect(screen.getByText('?')).toBeInTheDocument();
  });
});
