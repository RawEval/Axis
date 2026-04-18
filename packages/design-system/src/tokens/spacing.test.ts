import { describe, it, expect } from 'vitest';
import { SPACING, RADIUS, DURATION, EASING } from './spacing';

describe('spacing/radius/motion tokens', () => {
  it('SPACING is the artifact 4px-base scale', () => {
    expect(SPACING).toEqual([0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 56, 80]);
  });

  it('RADIUS includes md (default) and full (pill)', () => {
    expect(RADIUS.md).toBe(8);
    expect(RADIUS.full).toBe(999);
  });

  it('DURATION includes ambient breathing cycle (2400ms)', () => {
    expect(DURATION.ambient).toBe(2400);
  });

  it('EASING.spring is the artifact-prescribed stiffness/damping pair', () => {
    expect(EASING.spring).toEqual({ stiffness: 300, damping: 30 });
  });
});
