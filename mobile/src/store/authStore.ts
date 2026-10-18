import { create } from 'zustand';
import { clearToken, setToken } from '../api/client';

interface AuthUser {
  id: string;
  username: string;
  role: string;
}

interface AuthState {
  user: AuthUser | null;
  hydrated: boolean;
  login: (user: AuthUser, token: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: AuthUser | null) => void;
  setHydrated: (v: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  hydrated: false,
  login: async (user, token) => {
    await setToken(token);
    set({ user });
  },
  logout: async () => {
    await clearToken();
    set({ user: null });
  },
  setUser: (user) => set({ user }),
  setHydrated: (v) => set({ hydrated: v }),
}));
