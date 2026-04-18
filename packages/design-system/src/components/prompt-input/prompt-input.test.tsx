import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PromptInput } from './prompt-input';

describe('PromptInput', () => {
  it('renders the placeholder', () => {
    render(<PromptInput value="" onChange={() => {}} onSubmit={() => {}} placeholder="Ask Axis…" />);
    expect(screen.getByPlaceholderText('Ask Axis…')).toBeInTheDocument();
  });

  it('calls onChange while typing', async () => {
    const onChange = vi.fn();
    render(<PromptInput value="" onChange={onChange} onSubmit={() => {}} aria-label="prompt" />);
    await userEvent.type(screen.getByLabelText('prompt'), 'hi');
    // Two characters typed → onChange called twice
    expect(onChange).toHaveBeenCalledTimes(2);
  });

  it('calls onSubmit on ⌘+Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hello" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Meta>}{Enter}{/Meta}');
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('calls onSubmit on Ctrl+Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hello" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Control>}{Enter}{/Control}');
    expect(onSubmit).toHaveBeenCalledWith('hello');
  });

  it('does NOT submit on plain Enter', async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PromptInput value="hi" onChange={() => {}} onSubmit={onSubmit} aria-label="prompt" />);
    const ta = screen.getByLabelText('prompt');
    ta.focus();
    await user.keyboard('{Enter}');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit when the send button is clicked', async () => {
    const onSubmit = vi.fn();
    render(<PromptInput value="text" onChange={() => {}} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    expect(onSubmit).toHaveBeenCalledWith('text');
  });

  it('disables the send button when the value is empty', () => {
    render(<PromptInput value="" onChange={() => {}} onSubmit={() => {}} />);
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });

  it('disables both textarea and send when busy', () => {
    render(<PromptInput value="x" onChange={() => {}} onSubmit={() => {}} busy aria-label="prompt" />);
    expect(screen.getByLabelText('prompt')).toBeDisabled();
    expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
  });
});
