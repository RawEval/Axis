#!/usr/bin/env bash
# Sweeps dead Tailwind class names from old token system → new one.
# Run from repo root. Operates on apps/web/{app,components}/**/*.tsx in place.
# Idempotent; safe to run twice.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/apps/web"

if [[ ! -d "$WEB" ]]; then
  echo "fatal: $WEB not found" >&2
  exit 1
fi

# All file targets — only .tsx under app/ and components/.
# (Avoid `mapfile` for portability with macOS system bash 3.2.)
files=()
while IFS= read -r f; do
  files+=("$f")
done < <(find "$WEB/app" "$WEB/components" -type f -name '*.tsx' 2>/dev/null)

if [[ ${#files[@]} -eq 0 ]]; then
  echo "no .tsx files found"
  exit 0
fi

echo "Sweeping ${#files[@]} files…"

# Class-name substitutions. Order matters where prefixes overlap
# (longer / more-specific patterns must run first).
#
# Format: from|to
substitutions=(
  # Sub-shaded canvas
  'bg-canvas-raised|bg-canvas-surface'
  'bg-canvas-subtle|bg-canvas-elevated'
  # Old nav surface
  'bg-nav-active|bg-accent-subtle'
  'bg-nav-hover|bg-canvas-elevated'
  'bg-nav|bg-canvas-surface'
  # Brand → accent (longer numeric values first to avoid bg-brand-50 swallowing 500)
  'bg-brand-700|bg-accent-hover'
  'bg-brand-600|bg-accent-hover'
  'bg-brand-500|bg-accent'
  'bg-brand-200|bg-accent-subtle'
  'bg-brand-100|bg-accent-subtle'
  'bg-brand-50|bg-accent-subtle'
  'text-brand-700|text-accent'
  'text-brand-600|text-accent'
  'text-brand-500|text-accent'
  'border-brand-500|border-accent'
  'ring-brand-500|ring-accent'
  'hover:bg-brand-700|hover:bg-accent-hover'
  'hover:bg-brand-600|hover:bg-accent-hover'
  'hover:text-brand-600|hover:text-accent-hover'
  # Ink-on-dark legacy
  'text-ink-onDark/60|text-ink-secondary'
  'text-ink-onDark|text-ink'
  'border-ink-onDark|border-edge'
  'text-ink-disabled|text-ink-tertiary'
  # Semantic compound colors → flat semantic
  'bg-success-bg|bg-success/10'
  'text-success-fg|text-success'
  'border-success-border|border-success/30'
  'bg-warning-bg|bg-warning/10'
  'text-warning-fg|text-warning'
  'border-warning-border|border-warning/30'
  'bg-danger-bg|bg-danger/10'
  'text-danger-fg|text-danger'
  'border-danger-border|border-danger/30'
  'bg-info-bg|bg-info/10'
  'text-info-fg|text-info'
  'border-info-border|border-info/30'
  # Shadows
  'shadow-sm-strong|shadow-e1'
  'shadow-popover|shadow-e2'
  'shadow-panel|shadow-e1'
)

for sub in "${substitutions[@]}"; do
  from="${sub%%|*}"
  to="${sub#*|}"
  # Word-ish boundaries: don't replace if surrounded by other word chars.
  # Tailwind class strings are space- or quote-delimited, so we look for
  # boundaries that are NOT alnum/dash, AND don't allow trailing alnum/dash.
  pattern="(^|[^A-Za-z0-9-])($from)([^A-Za-z0-9-]|\$)"
  for f in "${files[@]}"; do
    # macOS / GNU sed compat: use perl -pi for portability.
    # Use {} delimiters for s{}{} so '/' inside patterns (e.g. text-ink-onDark/60,
    # bg-success/10) doesn't terminate the regex prematurely.
    perl -pi -e "s{$pattern}{\${1}$to\${3}}g" "$f"
  done
done

echo "done"
