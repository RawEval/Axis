'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../api';
import {
  type AuthUser,
  clearToken,
  getCachedUser,
  setCachedUser,
  setToken,
} from '../auth';

type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id?: string;
};

export function useLogin() {
  return useMutation({
    mutationFn: async (input: { email: string; password: string }) => {
      const res = await api.post<LoginResponse>('/auth/login', input);
      setToken(res.access_token);
      return res;
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: async (input: { email: string; password: string; name?: string }) => {
      const res = await api.post<LoginResponse>('/auth/register', input);
      setToken(res.access_token);
      return res;
    },
  });
}

export function useMe() {
  return useQuery<AuthUser>({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const user = await api.get<AuthUser>('/auth/me');
      setCachedUser(user);
      return user;
    },
    initialData: () => getCachedUser() ?? undefined,
    staleTime: 60_000,
  });
}

export function useLogout() {
  return () => {
    clearToken();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  };
}
