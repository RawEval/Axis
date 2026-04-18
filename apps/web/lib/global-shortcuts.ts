import { useEffect } from 'react';
import { useSyncExternalStore } from 'react';

interface OpenState {
  open: boolean;
}

function makeStore() {
  let state: OpenState = { open: false };
  const listeners = new Set<() => void>();
  const emit = () => {
    for (const l of listeners) l();
  };
  return {
    getState: (): OpenState => state,
    open: () => {
      if (state.open) return;
      state = { open: true };
      emit();
    },
    close: () => {
      if (!state.open) return;
      state = { open: false };
      emit();
    },
    toggle: () => {
      state = { open: !state.open };
      emit();
    },
    subscribe: (l: () => void) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
  };
}

export const commandPalette = makeStore();
export const shortcutOverlay = makeStore();

export function useCommandPalette(): OpenState {
  return useSyncExternalStore(
    commandPalette.subscribe,
    commandPalette.getState,
    commandPalette.getState,
  );
}

export function useShortcutOverlay(): OpenState {
  return useSyncExternalStore(
    shortcutOverlay.subscribe,
    shortcutOverlay.getState,
    shortcutOverlay.getState,
  );
}

/**
 * Mounts the global key handlers. Call once from the app shell.
 *  - ⌘K / Ctrl+K toggles the command palette.
 *  - ?  opens the shortcut overlay (only when not focused inside an input).
 *  - Escape closes whichever is open.
 */
export function useGlobalShortcuts(): void {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null;
      const inField =
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        commandPalette.toggle();
        return;
      }

      if (e.key === '?' && !inField) {
        e.preventDefault();
        shortcutOverlay.open();
        return;
      }

      if (e.key === 'Escape') {
        if (commandPalette.getState().open) commandPalette.close();
        if (shortcutOverlay.getState().open) shortcutOverlay.close();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}
