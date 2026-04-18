'use client';

import clsx from 'clsx';
import { useEffect, type ReactNode } from 'react';

/**
 * Minimal modal primitive. No portal — renders inline, escape + click-outside
 * close. Accessible-enough for Phase 1 (role="dialog", aria-modal).
 */
export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  widthClass?: string;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  widthClass = 'max-w-md',
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/30 p-4 pt-[15vh]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby={typeof title === 'string' ? 'modal-title' : undefined}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={clsx(
          'w-full rounded-md border border-edge bg-canvas-raised shadow-popover',
          widthClass,
        )}
      >
        {title && (
          <div className="border-b border-edge px-5 py-3">
            <div id="modal-title" className="text-sm font-semibold text-ink">
              {title}
            </div>
          </div>
        )}
        <div>{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-edge bg-canvas-subtle px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
