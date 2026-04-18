import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SegmentedControl } from './segmented-control';

describe('SegmentedControl', () => {
  const options = [
    { value: 'all', label: 'All' },
    { value: 'mine', label: 'Mine' },
    { value: 'team', label: 'Team' },
  ];

  it('renders each option label', () => {
    render(<SegmentedControl value="all" onChange={() => {}} options={options} />);
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('Mine')).toBeInTheDocument();
    expect(screen.getByText('Team')).toBeInTheDocument();
  });

  it('marks the active option', () => {
    render(<SegmentedControl value="mine" onChange={() => {}} options={options} />);
    expect(screen.getByRole('button', { name: 'Mine' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onChange with the new value when a button is clicked', async () => {
    const onChange = vi.fn();
    render(<SegmentedControl value="all" onChange={onChange} options={options} />);
    await userEvent.click(screen.getByText('Team'));
    expect(onChange).toHaveBeenCalledWith('team');
  });

  it('does not call onChange when the active option is clicked', async () => {
    const onChange = vi.fn();
    render(<SegmentedControl value="all" onChange={onChange} options={options} />);
    await userEvent.click(screen.getByText('All'));
    expect(onChange).not.toHaveBeenCalled();
  });
});
