import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PermissionCard } from './permission-card';

describe('PermissionCard', () => {
  const baseProps = {
    capability: 'connector.notion.read',
    description: 'Axis wants to read your Notion docs.',
    onAllow: vi.fn(),
    onDeny: vi.fn(),
  };

  it('renders capability and description', () => {
    render(<PermissionCard {...baseProps} />);
    expect(screen.getByText('connector.notion.read')).toBeInTheDocument();
    expect(screen.getByText(/wants to read/)).toBeInTheDocument();
  });

  it('renders four allow buttons + one deny button', () => {
    render(<PermissionCard {...baseProps} />);
    expect(screen.getByRole('button', { name: /allow once/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow for project/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow 24h/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /allow forever/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^deny$/i })).toBeInTheDocument();
  });

  it('fires onAllow with the chosen lifetime', async () => {
    const onAllow = vi.fn();
    render(<PermissionCard {...baseProps} onAllow={onAllow} />);
    await userEvent.click(screen.getByRole('button', { name: /allow for project/i }));
    expect(onAllow).toHaveBeenCalledWith('project');
  });

  it('fires onDeny when Deny is clicked', async () => {
    const onDeny = vi.fn();
    render(<PermissionCard {...baseProps} onDeny={onDeny} />);
    await userEvent.click(screen.getByRole('button', { name: /^deny$/i }));
    expect(onDeny).toHaveBeenCalled();
  });

  it('renders inputs preview when provided', () => {
    render(
      <PermissionCard {...baseProps} inputs={{ workspace: 'engineering' }} />,
    );
    expect(screen.getByText(/workspace/)).toBeInTheDocument();
    expect(screen.getByText(/engineering/)).toBeInTheDocument();
  });

  it('disables all buttons when busy is set', () => {
    render(<PermissionCard {...baseProps} busy="project" />);
    expect(screen.getByRole('button', { name: /allow once/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /allow for project/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^deny$/i })).toBeDisabled();
  });
});
