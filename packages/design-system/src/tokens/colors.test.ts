import { describe, it, expect } from 'vitest';
import { COLORS_DARK, COLORS_LIGHT, cssVar } from './colors';

describe('color tokens', () => {
  it('dark and light palettes share identical token keys', () => {
    expect(Object.keys(COLORS_DARK).sort()).toEqual(Object.keys(COLORS_LIGHT).sort());
  });

  it('cssVar generates kebab-cased CSS custom property names', () => {
    expect(cssVar('bg.canvas')).toBe('--color-bg-canvas');
    expect(cssVar('agent.thinking')).toBe('--color-agent-thinking');
  });

  it('every token has a non-empty hex string in both palettes', () => {
    for (const token of Object.keys(COLORS_DARK) as Array<keyof typeof COLORS_DARK>) {
      expect(COLORS_DARK[token]).toMatch(/^#[0-9A-F]{6}$/i);
      expect(COLORS_LIGHT[token]).toMatch(/^#[0-9A-F]{6}$/i);
    }
  });
});
