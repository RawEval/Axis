import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@/lib/theme';
import { TopBar } from './top-bar';

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}));

function rendered() {
  return render(
    <ThemeProvider>
      <TopBar />
    </ThemeProvider>,
  );
}

describe('TopBar', () => {
  it('renders the ⌘K chip and opens the palette when clicked', async () => {
    rendered();
    const btn = screen.getByRole('button', { name: /open command palette/i });
    expect(btn).toBeInTheDocument();
    expect(btn).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('renders the theme toggle', () => {
    rendered();
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument();
  });

  it('renders an account avatar/menu trigger', () => {
    rendered();
    expect(screen.getByRole('button', { name: /account/i })).toBeInTheDocument();
  });
});
