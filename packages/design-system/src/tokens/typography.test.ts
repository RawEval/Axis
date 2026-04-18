import { describe, it, expect } from 'vitest';
import { FONT_FAMILY, TYPE_SCALE } from './typography';

describe('typography tokens', () => {
  it('exposes display/sans/mono families', () => {
    expect(FONT_FAMILY.display).toContain('Inter Display');
    expect(FONT_FAMILY.sans).toContain('Inter');
    expect(FONT_FAMILY.mono).toContain('JetBrains Mono');
  });

  it('every scale entry has [size, lineHeight, tracking]', () => {
    for (const [, value] of Object.entries(TYPE_SCALE)) {
      expect(value).toHaveLength(3);
      expect(typeof value[0]).toBe('number');
    }
  });
});
