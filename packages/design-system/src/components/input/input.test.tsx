import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Input } from './input';

describe('Input', () => {
  it('renders with placeholder', () => {
    render(<Input placeholder="you@company.com" />);
    expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument();
  });

  it('accepts user input', async () => {
    render(<Input aria-label="email" />);
    await userEvent.type(screen.getByLabelText('email'), 'a@b.com');
    expect(screen.getByLabelText('email')).toHaveValue('a@b.com');
  });

  it('forwards ref', () => {
    let captured: HTMLInputElement | null = null;
    render(<Input ref={(el) => (captured = el)} aria-label="x" />);
    expect(captured).toBeInstanceOf(HTMLInputElement);
  });

  it('renders an error state with aria-invalid', () => {
    render(<Input invalid aria-label="email" />);
    expect(screen.getByLabelText('email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('honors `disabled`', async () => {
    render(<Input disabled aria-label="off" />);
    expect(screen.getByLabelText('off')).toBeDisabled();
  });
});
