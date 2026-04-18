'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
      setError('password must be at least 12 characters');
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
            : 'signup failed'
          : 'signup failed',
      );
    }
  };

  return (
    <Panel>
      <PanelHeader>
        <div>
          <div className="text-base font-semibold text-ink">Create account</div>
          <div className="text-xs text-ink-tertiary">Start with a 14-day trial. No card.</div>
        </div>
      </PanelHeader>
      <form onSubmit={onSubmit}>
        <PanelBody className="space-y-4">
          <Field label="Name">
            <Input
              type="text"
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
            <div className="rounded border border-danger/20 bg-danger-bg px-3 py-2 text-xs text-danger-fg">
              {error}
            </div>
          )}
          <Button
            type="submit"
            size="md"
            className="w-full"
            disabled={register.isPending}
          >
            {register.isPending ? 'Creating account…' : 'Create account'}
          </Button>
          <div className="text-center text-xs text-ink-tertiary">
            Have an account?{' '}
            <Link href="/login" className="text-brand-500 hover:text-brand-600">
              Sign in
            </Link>
          </div>
        </PanelBody>
      </form>
    </Panel>
  );
}
