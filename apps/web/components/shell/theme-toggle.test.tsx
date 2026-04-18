import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/lib/theme';
import { ThemeToggle } from './theme-toggle';

function renderWithTheme(ui: React.ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>);
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('renders a button labelled with the current theme', () => {
    renderWithTheme(<ThemeToggle />);
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument();
  });

  it('opens a menu of system / light / dark options', async () => {
    renderWithTheme(<ThemeToggle />);
    await userEvent.click(screen.getByRole('button', { name: /theme/i }));
    expect(await screen.findByText(/system/i)).toBeInTheDocument();
    expect(screen.getByText(/light/i)).toBeInTheDocument();
    expect(screen.getByText(/dark/i)).toBeInTheDocument();
  });

  it('switches theme when an option is selected', async () => {
    renderWithTheme(<ThemeToggle />);
    await userEvent.click(screen.getByRole('button', { name: /theme/i }));
    await userEvent.click(await screen.findByText(/light/i));
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });
});
