import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LeftNav } from './left-nav';

vi.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}));

describe('LeftNav', () => {
  it('renders the primary nav items with labels when expanded', () => {
    render(<LeftNav />);
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Activity')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Memory')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
  });

  it('marks the active route', () => {
    render(<LeftNav />);
    const chatLink = screen.getByRole('link', { name: /chat/i });
    expect(chatLink).toHaveAttribute('aria-current', 'page');
  });

  it('hides labels when collapsed', async () => {
    render(<LeftNav />);
    await userEvent.click(screen.getByRole('button', { name: /collapse/i }));
    expect(screen.queryByText('Home')).not.toBeInTheDocument();
  });

  it('shows labels again when expanded', async () => {
    render(<LeftNav />);
    await userEvent.click(screen.getByRole('button', { name: /collapse/i }));
    await userEvent.click(screen.getByRole('button', { name: /expand/i }));
    expect(screen.getByText('Home')).toBeInTheDocument();
  });

  it('renders the secondary nav (Connections, Team, Settings)', () => {
    render(<LeftNav />);
    expect(screen.getByText('Connections')).toBeInTheDocument();
    expect(screen.getByText('Team')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });
});
