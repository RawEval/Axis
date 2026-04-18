import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Kbd } from './kbd';

describe('Kbd', () => {
  it('renders the key label', () => {
    render(<Kbd>⌘K</Kbd>);
    expect(screen.getByText('⌘K')).toBeInTheDocument();
  });

  it('uses mono font + border', () => {
    render(<Kbd data-testid="k">A</Kbd>);
    const el = screen.getByTestId('k');
    expect(el).toHaveClass('font-mono');
    expect(el).toHaveClass('border');
  });

  it('renders inside a kbd element', () => {
    render(<Kbd>X</Kbd>);
    expect(screen.getByText('X').tagName).toBe('KBD');
  });
});
