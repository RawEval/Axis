import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { shortcutOverlay } from '@/lib/global-shortcuts';
import { ShortcutOverlay } from './shortcut-overlay';

beforeEach(() => {
  act(() => {
    shortcutOverlay.close();
  });
});

describe('ShortcutOverlay', () => {
  it('renders nothing when closed', () => {
    render(<ShortcutOverlay />);
    expect(screen.queryByText(/keyboard shortcuts/i)).not.toBeInTheDocument();
  });

  it('renders shortcut categories when opened', () => {
    render(<ShortcutOverlay />);
    act(() => {
      shortcutOverlay.open();
    });
    expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
    expect(screen.getByText(/global/i)).toBeInTheDocument();
    expect(screen.getByText(/command palette/i)).toBeInTheDocument();
  });

  it('closes when Close button is clicked', async () => {
    render(<ShortcutOverlay />);
    act(() => {
      shortcutOverlay.open();
    });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(shortcutOverlay.getState().open).toBe(false);
  });
});
