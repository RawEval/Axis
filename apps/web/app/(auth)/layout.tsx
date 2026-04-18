export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <header className="flex h-12 items-center border-b border-edge bg-canvas-raised px-5">
        <div className="flex items-center gap-2 text-ink">
          <span className="h-2.5 w-2.5 rounded-sm bg-brand-500" aria-hidden />
          <span className="text-sm font-semibold tracking-tight">Axis</span>
        </div>
      </header>
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm">{children}</div>
      </div>
      <footer className="border-t border-edge bg-canvas-raised px-5 py-3 text-center text-xs text-ink-tertiary">
        Axis · v0.1.0 · © 2026 RawEval Inc
      </footer>
    </div>
  );
}
