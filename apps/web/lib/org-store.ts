'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Active organization store. Like the project store but one level up.
 * Empty string means "use the user's personal org by default."
 */
type OrgStore = {
  activeOrg: string;
  setActiveOrg: (id: string) => void;
};

export const useOrgStore = create<OrgStore>()(
  persist(
    (set) => ({
      activeOrg: '',
      setActiveOrg: (id) => set({ activeOrg: id }),
    }),
    { name: 'axis.active-org' },
  ),
);
