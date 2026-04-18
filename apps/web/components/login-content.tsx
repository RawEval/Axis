'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@axis/design-system';
import { Field, Input } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { useLogin } from '@/lib/queries/auth';

export default function LoginContent() {
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
            : 'Login failed.'
          : 'Login failed.',
      );
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-display-m text-ink">Sign in</h1>
        <p className="text-body text-ink-secondary">Welcome back.</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
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
          <div
            role="alert"
            className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-body-s text-danger"
          >
            {error}
          </div>
        )}

        <Button type="submit" size="md" className="w-full" loading={login.isPending}>
          Sign in
        </Button>
      </form>

      <p className="text-body-s text-ink-tertiary">
        No account?{' '}
        <Link
          href="/signup"
          className="text-accent hover:text-accent-hover underline-offset-4 hover:underline"
        >
          Create one
        </Link>
      </p>
    </div>
  );
}
