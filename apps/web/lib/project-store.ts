'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ProjectScope = string; // uuid | 'all' | 'auto'

type ProjectStore = {
  activeProject: ProjectScope;
  setActiveProject: (p: ProjectScope) => void;
};

/**
 * Zustand store for the active project.
 *
 * Persists to localStorage so the user's pick survives reloads. The value is
 * sent on every API call via the X-Axis-Project header from lib/api.ts.
 *
 * Special sentinels:
 *   - ''     → no preference (backend falls back to the user's default project)
 *   - 'all'  → fan-out over every project the user owns
 *   - 'auto' → let the agent classifier pick (Phase 2; falls back to default)
 *   - <uuid> → explicit pin
 */
export const useProjectStore = create<ProjectStore>()(
  persist(
    (set) => ({
      activeProject: '',
      setActiveProject: (p) => set({ activeProject: p }),
    }),
    { name: 'axis.active-project' },
  ),
);
