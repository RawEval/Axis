'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  /** max-width override (default 480px). */
  widthClass?: string;
}

const OVERLAY =
  'fixed inset-0 z-50 bg-black/60 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out';

const CONTENT =
  'fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full bg-canvas-surface border border-edge rounded-lg shadow-e3 outline-none max-h-[85vh] flex flex-col';

export function Modal({ open, onOpenChange, children, widthClass = 'max-w-[480px]' }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={OVERLAY} />
        <Dialog.Content className={clsx(CONTENT, widthClass)} aria-describedby={undefined}>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ModalTitle({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <Dialog.Title asChild>
      <h2 className={clsx('px-6 pt-6 pb-2 text-heading-2 text-ink', className)} {...rest}>
        {children}
      </h2>
    </Dialog.Title>
  );
}

export function ModalDescription({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <Dialog.Description asChild>
      <p className={clsx('px-6 text-body-s text-ink-secondary', className)} {...rest}>
        {children}
      </p>
    </Dialog.Description>
  );
}

export function ModalBody({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('px-6 py-4 overflow-y-auto', className)} {...rest}>
      {children}
    </div>
  );
}

export function ModalFooter({
  children,
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('px-6 pb-6 pt-2 flex items-center justify-end gap-3', className)} {...rest}>
      {children}
    </div>
  );
}
