import { create } from 'zustand';

type UiState = {
  activePrompt: string;
  setActivePrompt: (v: string) => void;
  trustLevel: 'low' | 'medium' | 'high';
  setTrustLevel: (t: UiState['trustLevel']) => void;
};

export const useUiStore = create<UiState>((set) => ({
  activePrompt: '',
  setActivePrompt: (v) => set({ activePrompt: v }),
  trustLevel: 'low',
  setTrustLevel: (t) => set({ trustLevel: t }),
}));
