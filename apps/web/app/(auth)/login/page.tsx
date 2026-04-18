'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import {
  Button,
  Field,
  Input,
  Panel,
  PanelBody,
  PanelHeader,
} from '@/components/ui';
import { ApiError } from '@/lib/api';
import { useLogin } from '@/lib/queries/auth';

export default function LoginPage() {
  const router = useRouter();
  const params = useSearchParams();
  const from = params.get('from') ?? '/feed';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const login = useLogin();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push(from);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'login failed'
          : 'login failed',
      );
    }
  };

  return (
    <Panel>
      <PanelHeader>
        <div>
          <div className="text-base font-semibold text-ink">Sign in</div>
          <div className="text-xs text-ink-tertiary">Welcome back.</div>
        </div>
      </PanelHeader>
      <form onSubmit={onSubmit}>
        <PanelBody className="space-y-4">
          <Field label="Email" required>
            <Input
              type="email"
              required
              autoFocus
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </Field>
          <Field label="Password" required>
            <Input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error && (
            <div className="rounded border border-danger/20 bg-danger-bg px-3 py-2 text-xs text-danger-fg">
              {error}
            </div>
          )}
          <Button
            type="submit"
            size="md"
            className="w-full"
            disabled={login.isPending}
          >
            {login.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
          <div className="text-center text-xs text-ink-tertiary">
            No account?{' '}
            <Link href="/signup" className="text-brand-500 hover:text-brand-600">
              Create one
            </Link>
          </div>
        </PanelBody>
      </form>
    </Panel>
  );
}
