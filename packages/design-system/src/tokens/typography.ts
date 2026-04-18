/** Typography tokens — see docs/compass_artifact §2b. */

export const FONT_FAMILY = {
  display: 'var(--font-display), "Inter Display", -apple-system, BlinkMacSystemFont, sans-serif',
  sans: 'var(--font-sans), "Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  mono: 'var(--font-mono), "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace',
} as const;

/** [size in px, line-height multiplier, letter-spacing em] */
export const TYPE_SCALE = {
  'display.xl':  [48, 1.05, -0.03],
  'display.l':   [36, 1.10, -0.025],
  'display.m':   [28, 1.15, -0.02],
  'heading.1':   [22, 1.25, -0.015],
  'heading.2':   [18, 1.30, -0.01],
  'heading.3':   [15, 1.35, -0.005],
  'body.l':      [16, 1.55, 0],
  'body':        [14, 1.50, 0],
  'body.s':      [13, 1.45, 0.005],
  'caption':     [12, 1.40, 0.01],
  'micro':       [11, 1.35, 0.04],
  'mono.l':      [14, 1.50, 0],
  'mono':        [13, 1.50, 0],
  'mono.s':      [12, 1.45, 0],
  'kbd':         [11, 1.00, 0.02],
} as const satisfies Record<string, readonly [number, number, number]>;

export type TypeScaleKey = keyof typeof TYPE_SCALE;
