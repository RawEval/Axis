import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LiveTaskTree, type StepData } from './live-task-tree';

const steps: StepData[] = [
  { id: '1', label: 'Read #product Slack', state: 'done', durationMs: 3200 },
  { id: '2', label: 'Read Notion: Q3 roadmap', state: 'done', durationMs: 5800 },
  {
    id: '3',
    label: 'Draft recap',
    state: 'running',
    toolCall: { name: 'notion.create_draft', args: { title: 'Q3 Engineering Recap' } },
  },
  { id: '4', label: 'Post to #leadership', state: 'pending' },
];

describe('LiveTaskTree', () => {
  it('renders one row per step', () => {
    render(<LiveTaskTree steps={steps} />);
    expect(screen.getByText('Read #product Slack')).toBeInTheDocument();
    expect(screen.getByText('Read Notion: Q3 roadmap')).toBeInTheDocument();
    expect(screen.getByText('Draft recap')).toBeInTheDocument();
    expect(screen.getByText('Post to #leadership')).toBeInTheDocument();
  });

  it('shows duration for completed steps', () => {
    render(<LiveTaskTree steps={steps} />);
    expect(screen.getByText('3.2s')).toBeInTheDocument();
    expect(screen.getByText('5.8s')).toBeInTheDocument();
  });

  it('renders nested children when provided', () => {
    const tree: StepData[] = [
      {
        id: 'p',
        label: 'Plan',
        state: 'running',
        children: [
          { id: 'p-1', label: 'Substep one', state: 'done', durationMs: 100 },
          { id: 'p-2', label: 'Substep two', state: 'pending' },
        ],
      },
    ];
    render(<LiveTaskTree steps={tree} />);
    expect(screen.getByText('Plan')).toBeInTheDocument();
    expect(screen.getByText('Substep one')).toBeInTheDocument();
    expect(screen.getByText('Substep two')).toBeInTheDocument();
  });

  it('renders nothing when steps is empty', () => {
    const { container } = render(<LiveTaskTree steps={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('expands tool I/O on click when toolCall is present', async () => {
    render(<LiveTaskTree steps={steps} />);
    const expandButton = screen.getByRole('button', { name: /expand notion\.create_draft/i });
    await userEvent.click(expandButton);
    expect(screen.getByText(/Q3 Engineering Recap/)).toBeInTheDocument();
  });

  it('marks running steps with the running animation class', () => {
    render(<LiveTaskTree steps={steps} />);
    const runningRow = screen.getByText('Draft recap').closest('div');
    expect(runningRow?.querySelector('span.animate-breathe')).toBeInTheDocument();
  });
});
