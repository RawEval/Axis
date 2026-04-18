'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button } from '@axis/design-system';
import { Field, Input } from '@/components/ui';
import { ApiError } from '@/lib/api';
import { useRegister } from '@/lib/queries/auth';

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const register = useRegister();

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 12) {
      setError('Password must be at least 12 characters.');
      return;
    }
    try {
      await register.mutateAsync({ email, password, name: name || undefined });
      router.push('/feed');
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'Signup failed.'
          : 'Signup failed.',
      );
    }
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="font-display text-display-m text-ink">Create your account</h1>
        <p className="text-body text-ink-secondary">Work email recommended.</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label="Name">
          <Input
            type="text"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Full name"
          />
        </Field>

        <Field label="Work email" required>
          <Input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
        </Field>

        <Field label="Password" hint="Minimum 12 characters." required>
          <Input
            type="password"
            required
            minLength={12}
            autoComplete="new-password"
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

        <Button type="submit" size="md" className="w-full" loading={register.isPending}>
          Create account
        </Button>
      </form>

      <p className="text-body-s text-ink-tertiary">
        Already have an account?{' '}
        <Link
          href="/login"
          className="text-accent hover:text-accent-hover underline-offset-4 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
