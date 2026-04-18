/** Spacing, radius, motion tokens — see docs/compass_artifact §2c. */

export const SPACING = [0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 80] as const;

export const RADIUS = {
  none: 0,
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 999,
} as const;

export const DURATION = {
  micro: 120,
  short: 200,
  medium: 280,
  long: 400,
  ambient: 2400,
  shimmer: 1400,
} as const;

export const EASING = {
  spring: { stiffness: 300, damping: 30 },
  easeOut: 'cubic-bezier(0.2, 0, 0, 1)',
  easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  linear: 'linear',
} as const;
