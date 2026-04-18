import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '@/lib/theme';
import { commandPalette } from '@/lib/global-shortcuts';
import { CommandPalette } from './command-palette';

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
  usePathname: () => '/',
}));

beforeEach(() => {
  pushMock.mockReset();
  act(() => {
    commandPalette.close();
  });
});

function rendered() {
  return render(
    <ThemeProvider>
      <CommandPalette />
    </ThemeProvider>,
  );
}

describe('CommandPalette', () => {
  it('renders nothing when the store is closed', () => {
    rendered();
    expect(screen.queryByPlaceholderText(/search…/i)).not.toBeInTheDocument();
  });

  it('renders the search input + nav category when opened', () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    expect(screen.getByPlaceholderText(/search…/i)).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Activity')).toBeInTheDocument();
  });

  it('navigates and closes when a nav item is selected', async () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    await userEvent.click(screen.getByText('Chat'));
    expect(pushMock).toHaveBeenCalledWith('/chat');
    expect(commandPalette.getState().open).toBe(false);
  });

  it('exposes theme switching items', () => {
    rendered();
    act(() => {
      commandPalette.open();
    });
    expect(screen.getByText(/light theme/i)).toBeInTheDocument();
    expect(screen.getByText(/dark theme/i)).toBeInTheDocument();
  });
});
