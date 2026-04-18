import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('fires onClick', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies the variant class for primary by default', () => {
    render(<Button>Primary</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-accent');
  });

  it('renders the danger variant with a danger background', () => {
    render(<Button variant="danger">Delete</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-danger');
  });

  it('renders the secondary variant with a border', () => {
    render(<Button variant="secondary">More</Button>);
    expect(screen.getByRole('button')).toHaveClass('border');
  });

  it('disables interaction when `disabled`', async () => {
    const onClick = vi.fn();
    render(<Button disabled onClick={onClick}>Off</Button>);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('renders the loading state with aria-busy', () => {
    render(<Button loading>Submit</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toHaveAttribute('aria-busy', 'true');
    expect(btn).toBeDisabled();
  });

  it('respects `size` prop', () => {
    const { rerender } = render(<Button size="sm">sm</Button>);
    expect(screen.getByRole('button')).toHaveClass('h-8');
    rerender(<Button size="lg">lg</Button>);
    expect(screen.getByRole('button')).toHaveClass('h-12');
  });
});
