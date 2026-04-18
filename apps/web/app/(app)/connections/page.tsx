import { Suspense } from 'react';
import { Skeleton } from '@axis/design-system';
import ConnectionsContent from '@/components/connections-content';
import type { Tool } from '@/lib/queries/connectors';

const TOOLS: Array<{
  tool: Tool;
  label: string;
  icon: string;
  color: string;
  desc: string;
}> = [
  { tool: 'slack', label: 'Slack', icon: '#', color: 'bg-[#4A154B]', desc: 'Messages, channels, threads' },
  { tool: 'notion', label: 'Notion', icon: 'N', color: 'bg-[#000000]', desc: 'Pages, databases, docs' },
  { tool: 'gmail', label: 'Gmail', icon: 'M', color: 'bg-[#EA4335]', desc: 'Inbox, search, send' },
  { tool: 'gdrive', label: 'Drive', icon: 'D', color: 'bg-[#4285F4]', desc: 'Files, docs, sheets' },
  { tool: 'github', label: 'GitHub', icon: 'G', color: 'bg-[#24292e]', desc: 'Issues, PRs, repos' },
];

function LoadingConnections() {
  return (
    <div className="mx-auto flex min-h-full max-w-5xl flex-col gap-6 px-6 py-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4].map((i) => (
          <Skeleton key={i} height={160} rounded="lg" />
        ))}
      </div>
    </div>
  );
}

export default function ConnectionsPage() {
  return (
    <Suspense fallback={<LoadingConnections />}>
      <ConnectionsContent tools={TOOLS} />
    </Suspense>
  );
}
