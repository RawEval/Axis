import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TargetPicker, type TargetCandidate } from './target-picker';

const SAMPLE: TargetCandidate[] = [
  {
    kind: 'email_address',
    id: 'mrinal@a.com',
    label: 'Mrinal Raj',
    sub_label: 'mrinal@a.com',
    context: 'Last replied 2d ago',
  },
  {
    kind: 'email_address',
    id: 'mrinal@b.com',
    label: 'Mrinal Patel',
    sub_label: 'mrinal@b.com',
    context: null,
  },
];

describe('TargetPicker', () => {
  it('renders one button per candidate', () => {
    render(<TargetPicker candidates={SAMPLE} onChoose={() => {}} />);
    expect(screen.getByRole('button', { name: /Mrinal Raj/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mrinal Patel/ })).toBeInTheDocument();
  });

  it('shows the helper prompt', () => {
    render(<TargetPicker candidates={SAMPLE} onChoose={() => {}} prompt="Which Mrinal?" />);
    expect(screen.getByText('Which Mrinal?')).toBeInTheDocument();
  });

  it('fires onChoose with the candidate', async () => {
    const onChoose = vi.fn();
    render(<TargetPicker candidates={SAMPLE} onChoose={onChoose} />);
    await userEvent.click(screen.getByRole('button', { name: /Mrinal Raj/ }));
    expect(onChoose).toHaveBeenCalledWith(SAMPLE[0]);
  });

  it('marks the busy candidate with aria-busy and disables all', () => {
    render(<TargetPicker candidates={SAMPLE} onChoose={() => {}} busy={SAMPLE[0].id} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toHaveAttribute('aria-busy', 'true');
    expect(buttons[0]).toBeDisabled();
    expect(buttons[1]).toBeDisabled();
  });

  it('renders sub_label and context when provided', () => {
    render(<TargetPicker candidates={SAMPLE} onChoose={() => {}} />);
    expect(screen.getByText('mrinal@a.com')).toBeInTheDocument();
    expect(screen.getByText('Last replied 2d ago')).toBeInTheDocument();
  });
});
