/**
 * Color tokens — see docs/compass_artifact §2a.
 * Values are exposed as CSS custom properties in apps/web/app/globals.css.
 * Component code should reference the CSS-var name (e.g. `var(--color-bg-canvas)`)
 * via Tailwind utility classes (`bg-canvas`, `text-ink`, etc.) wired in tailwind.config.ts.
 */

export type ColorToken =
  | 'bg.canvas' | 'bg.surface' | 'bg.elevated' | 'bg.sunken'
  | 'border.subtle' | 'border.default' | 'border.strong'
  | 'text.primary' | 'text.secondary' | 'text.tertiary' | 'text.inverse'
  | 'accent.primary' | 'accent.hover' | 'accent.subtle' | 'accent.on'
  | 'success' | 'warning' | 'danger' | 'info'
  | 'agent.thinking' | 'agent.running' | 'agent.awaiting'
  | 'agent.recovered' | 'agent.blocked' | 'agent.background';

export const COLORS_DARK: Record<ColorToken, string> = {
  'bg.canvas': '#09090B',
  'bg.surface': '#111113',
  'bg.elevated': '#1A1A1D',
  'bg.sunken': '#060608',
  'border.subtle': '#27272A',
  'border.default': '#3F3F46',
  'border.strong': '#52525B',
  'text.primary': '#FAFAFA',
  'text.secondary': '#A1A1AA',
  'text.tertiary': '#71717A',
  'text.inverse': '#09090B',
  'accent.primary': '#4F5AF0',
  'accent.hover': '#6B74F3',
  'accent.subtle': '#1C1E3D',
  'accent.on': '#FFFFFF',
  'success': '#34D399',
  'warning': '#F5A524',
  'danger': '#F87171',
  'info': '#60A5FA',
  'agent.thinking': '#9CA3F7',
  'agent.running': '#4F5AF0',
  'agent.awaiting': '#F5A524',
  'agent.recovered': '#34D399',
  'agent.blocked': '#F87171',
  'agent.background': '#71717A',
};

export const COLORS_LIGHT: Record<ColorToken, string> = {
  'bg.canvas': '#F7F6F3',
  'bg.surface': '#FFFFFF',
  'bg.elevated': '#FAFAF8',
  'bg.sunken': '#EFEDE8',
  'border.subtle': '#E7E5E0',
  'border.default': '#D4D1CA',
  'border.strong': '#A8A49A',
  'text.primary': '#0E0E10',
  'text.secondary': '#55545A',
  'text.tertiary': '#89878F',
  'text.inverse': '#FAFAFA',
  'accent.primary': '#3340E6',
  'accent.hover': '#202CD4',
  'accent.subtle': '#E8EAFE',
  'accent.on': '#FFFFFF',
  'success': '#059669',
  'warning': '#B45309',
  'danger': '#DC2626',
  'info': '#2563EB',
  'agent.thinking': '#6366F1',
  'agent.running': '#3340E6',
  'agent.awaiting': '#B45309',
  'agent.recovered': '#059669',
  'agent.blocked': '#DC2626',
  'agent.background': '#89878F',
};

/** CSS custom-property name for a token (e.g. 'bg.canvas' → '--color-bg-canvas'). */
export const cssVar = (token: ColorToken): string =>
  `--color-${token.replace(/\./g, '-')}`;
