import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom doesn't implement ResizeObserver (cmdk needs it)
class ResizeObserverPolyfill {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
(globalThis as { ResizeObserver?: typeof ResizeObserverPolyfill }).ResizeObserver =
  ResizeObserverPolyfill;

// jsdom doesn't implement Element.scrollIntoView (cmdk auto-scrolls selected item)
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = function () {};
}
