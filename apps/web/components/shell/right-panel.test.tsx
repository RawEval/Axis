import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rightPanel } from '@/lib/right-panel';
import { RightPanel } from './right-panel';
import { act } from '@testing-library/react';

describe('RightPanel component', () => {
  beforeEach(() => {
    act(() => {
      rightPanel.close();
    });
  });

  it('renders nothing when store is closed', () => {
    render(<RightPanel />);
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });

  it('renders title + body when opened', () => {
    render(<RightPanel />);
    act(() => {
      rightPanel.open({ title: 'Run', body: 'details here' });
    });
    expect(screen.getByText('Run')).toBeInTheDocument();
    expect(screen.getByText('details here')).toBeInTheDocument();
  });

  it('closes when the close button is clicked', async () => {
    render(<RightPanel />);
    act(() => {
      rightPanel.open({ title: 'Run', body: 'x' });
    });
    await userEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(screen.queryByText('Run')).not.toBeInTheDocument();
  });
});
