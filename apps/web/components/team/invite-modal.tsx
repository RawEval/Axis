'use client';

import { useState } from 'react';
import {
  Button,
  Field,
  Input,
  Modal,
  Select,
  Textarea,
} from '@/components/ui';
import { ApiError } from '@/lib/api';
import {
  ROLE_DESCRIPTIONS,
  ROLE_LABELS,
  type Role,
  inviteableRoles,
  useCreateInvite,
} from '@/lib/queries/orgs';

export function InviteModal({
  open,
  onClose,
  orgId,
  myRole,
}: {
  open: boolean;
  onClose: () => void;
  orgId: string;
  myRole: Role;
}) {
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<Role>('member');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [acceptUrl, setAcceptUrl] = useState<string | null>(null);

  const create = useCreateInvite(orgId);
  const available = inviteableRoles(myRole);

  const reset = () => {
    setEmail('');
    setRole('member');
    setNote('');
    setError(null);
    setAcceptUrl(null);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const inv = await create.mutateAsync({
        email: email.trim(),
        role,
        note: note.trim() || undefined,
      });
      if (inv.accept_url && typeof window !== 'undefined') {
        setAcceptUrl(`${window.location.origin}${inv.accept_url}`);
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? typeof err.detail === 'string'
            ? err.detail
            : 'invite failed'
          : 'invite failed',
      );
    }
  };

  const copyLink = async () => {
    if (!acceptUrl) return;
    try {
      await navigator.clipboard.writeText(acceptUrl);
    } catch {
      /* clipboard might be blocked; link is still visible */
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Invite a teammate"
      widthClass="max-w-lg"
      footer={
        acceptUrl ? (
          <Button variant="primary" size="sm" onClick={handleClose}>
            Done
          </Button>
        ) : (
          <>
            <Button variant="ghost" size="sm" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onSubmit}
              disabled={create.isPending || !email.trim()}
            >
              {create.isPending ? 'Creating…' : 'Create invite'}
            </Button>
          </>
        )
      }
    >
      <div className="px-5 py-4">
        {acceptUrl ? (
          <div className="space-y-3">
            <p className="text-sm text-ink-secondary">
              Share this link with your teammate. They&apos;ll be prompted to sign in
              or create an account with the matching email.
            </p>
            <div className="flex items-center gap-2 rounded border border-edge bg-canvas-elevated px-3 py-2">
              <code className="flex-1 truncate font-mono text-xs text-ink">
                {acceptUrl}
              </code>
              <Button variant="secondary" size="sm" onClick={copyLink}>
                Copy
              </Button>
            </div>
            <p className="text-xs text-ink-tertiary">
              Email delivery is not yet enabled in this environment — share the
              link over Slack or iMessage for now.
            </p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <Field label="Email" required>
              <Input
                type="email"
                autoFocus
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teammate@company.com"
              />
            </Field>
            <Field label="Role" required hint={ROLE_DESCRIPTIONS[role]}>
              <Select
                value={role}
                onChange={(e) => setRole(e.target.value as Role)}
              >
                {available.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field
              label="Note (optional)"
              hint="Shown to the recipient. Context for why you're inviting them."
            >
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                maxLength={500}
              />
            </Field>
            {error && (
              <div className="rounded border border-danger/20 bg-danger/10 px-3 py-2 text-xs text-danger">
                {error}
              </div>
            )}
          </form>
        )}
      </div>
    </Modal>
  );
}
