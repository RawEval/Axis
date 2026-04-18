'use client';

const TOKEN_KEY = 'axis.token';
const USER_KEY = 'axis.user';

export type AuthUser = {
  id: string;
  email: string;
  name: string | null;
  plan: 'free' | 'pro' | 'team' | 'enterprise';
  created_at: string;
};

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(TOKEN_KEY, token);
  // mirror to cookie so middleware.ts can read it on server
  document.cookie = `${TOKEN_KEY}=${token}; path=/; max-age=${60 * 60}; samesite=lax`;
}

export function clearToken(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
}

export function getCachedUser(): AuthUser | null {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setCachedUser(user: AuthUser): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export const AXIS_TOKEN_COOKIE = TOKEN_KEY;
