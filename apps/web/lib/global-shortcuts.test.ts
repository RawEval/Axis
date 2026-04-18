import { describe, it, expect, beforeEach } from 'vitest';
import { commandPalette, shortcutOverlay } from './global-shortcuts';

describe('global-shortcuts stores', () => {
  beforeEach(() => {
    commandPalette.close();
    shortcutOverlay.close();
  });

  it('command palette starts closed', () => {
    expect(commandPalette.getState().open).toBe(false);
  });

  it('command palette toggle flips state', () => {
    commandPalette.toggle();
    expect(commandPalette.getState().open).toBe(true);
    commandPalette.toggle();
    expect(commandPalette.getState().open).toBe(false);
  });

  it('shortcut overlay opens and closes', () => {
    shortcutOverlay.open();
    expect(shortcutOverlay.getState().open).toBe(true);
    shortcutOverlay.close();
    expect(shortcutOverlay.getState().open).toBe(false);
  });
});
