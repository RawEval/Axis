import type { ReactNode } from 'react';

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[420px_1fr] bg-canvas">
      <section className="flex flex-col px-8 py-10 lg:px-10 lg:py-14 bg-canvas">
        <header className="mb-12 flex items-center gap-2">
          <span aria-hidden className="block h-3 w-3 rounded-sm bg-accent" />
          <span className="font-display text-heading-1 text-ink">Axis</span>
        </header>
        <main className="flex-1 flex flex-col justify-center max-w-[360px]">
          {children}
        </main>
        <footer className="mt-12 text-caption text-ink-tertiary">
          Axis · v0.1 · © 2026 RawEval Inc
        </footer>
      </section>

      <aside
        aria-hidden
        className="hidden lg:block bg-canvas-surface border-l border-edge-subtle relative overflow-hidden"
      >
        <div className="absolute inset-0 flex items-center justify-center text-ink-tertiary">
          <span className="font-mono text-caption uppercase tracking-[0.12em]">
            preview canvas — coming soon
          </span>
        </div>
      </aside>
    </div>
  );
}
