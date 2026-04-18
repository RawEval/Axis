import { describe, it, expect, beforeEach } from 'vitest';
import { rightPanel } from './right-panel';

describe('rightPanel store', () => {
  beforeEach(() => {
    rightPanel.close();
  });

  it('starts closed', () => {
    expect(rightPanel.getState().open).toBe(false);
  });

  it('opens with a node', () => {
    rightPanel.open({ title: 'Run details', body: 'placeholder' });
    expect(rightPanel.getState().open).toBe(true);
    expect(rightPanel.getState().title).toBe('Run details');
  });

  it('closes', () => {
    rightPanel.open({ title: 'x', body: 'y' });
    rightPanel.close();
    expect(rightPanel.getState().open).toBe(false);
  });
});
