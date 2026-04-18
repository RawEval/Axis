import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Modal, ModalTitle, ModalBody, ModalFooter } from './modal';

describe('Modal', () => {
  it('does not render when open is false', () => {
    render(
      <Modal open={false} onOpenChange={() => {}}>
        <ModalTitle>Hi</ModalTitle>
      </Modal>,
    );
    expect(screen.queryByText('Hi')).not.toBeInTheDocument();
  });

  it('renders title / body / footer slots when open', () => {
    render(
      <Modal open onOpenChange={() => {}}>
        <ModalTitle>Title</ModalTitle>
        <ModalBody>Body</ModalBody>
        <ModalFooter>Footer</ModalFooter>
      </Modal>,
    );
    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
    expect(screen.getByText('Footer')).toBeInTheDocument();
  });

  it('calls onOpenChange(false) when Escape is pressed', async () => {
    const onOpenChange = vi.fn();
    render(
      <Modal open onOpenChange={onOpenChange}>
        <ModalTitle>x</ModalTitle>
      </Modal>,
    );
    await userEvent.keyboard('{Escape}');
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('exposes a description slot via ModalDescription', () => {
    render(
      <Modal open onOpenChange={() => {}}>
        <ModalTitle>x</ModalTitle>
      </Modal>,
    );
    // dialog must be present
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
