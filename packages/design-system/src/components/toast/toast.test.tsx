import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastViewport, useToasts, toast } from './toast';

describe('Toast', () => {
  beforeEach(() => {
    // reset toast store
    useToasts.setState({ toasts: [] });
  });

  it('renders no toasts initially', () => {
    render(<ToastViewport />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('shows a toast when toast.success is called', () => {
    render(<ToastViewport />);
    act(() => {
      toast.success('Saved');
    });
    expect(screen.getByText('Saved')).toBeInTheDocument();
  });

  it('shows an undo toast with an Undo button', async () => {
    const onUndo = vi.fn();
    render(<ToastViewport />);
    act(() => {
      toast.action('Sent message', { actionLabel: 'Undo', onAction: onUndo });
    });
    expect(screen.getByText('Sent message')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Undo' }));
    expect(onUndo).toHaveBeenCalledTimes(1);
  });

  it('removes a toast when its dismiss icon is clicked', async () => {
    render(<ToastViewport />);
    act(() => {
      toast.info('Hello');
    });
    expect(screen.getByText('Hello')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(screen.queryByText('Hello')).not.toBeInTheDocument();
  });

  it('renders the danger tone for error toasts', () => {
    render(<ToastViewport />);
    act(() => {
      toast.error('Failed');
    });
    expect(screen.getByText('Failed').closest('[role="status"]')).toHaveClass('border-danger/30');
  });
});
