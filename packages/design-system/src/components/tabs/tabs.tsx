'use client';

import * as T from '@radix-ui/react-tabs';
import clsx from 'clsx';
import { forwardRef, type ComponentPropsWithoutRef } from 'react';

export const Tabs = T.Root;

const LIST = 'inline-flex items-end gap-4 border-b border-edge-subtle';

export const TabsList = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof T.List>
>(function TabsList({ className, ...rest }, ref) {
  return <T.List ref={ref} className={clsx(LIST, className)} {...rest} />;
});

const TRIGGER =
  'h-10 -mb-px px-1 text-body-s font-medium text-ink-secondary border-b-2 border-transparent hover:text-ink data-[state=active]:text-ink data-[state=active]:border-accent transition-colors';

export const TabsTrigger = forwardRef<
  HTMLButtonElement,
  ComponentPropsWithoutRef<typeof T.Trigger>
>(function TabsTrigger({ className, ...rest }, ref) {
  return <T.Trigger ref={ref} className={clsx(TRIGGER, className)} {...rest} />;
});

export const TabsContent = forwardRef<
  HTMLDivElement,
  ComponentPropsWithoutRef<typeof T.Content>
>(function TabsContent({ className, ...rest }, ref) {
  return <T.Content ref={ref} className={clsx('pt-6 outline-none', className)} {...rest} />;
});
