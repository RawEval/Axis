'use client';

export type TaskNode = {
  id: string;
  agent: string;
  tool?: string;
  status: 'pending' | 'running' | 'done' | 'error';
  elapsedMs?: number;
  children?: TaskNode[];
};

const STATUS_DOT: Record<TaskNode['status'], string> = {
  pending: 'bg-ink-disabled',
  running: 'bg-brand-500 animate-pulse',
  done: 'bg-success',
  error: 'bg-danger',
};

export function TaskTree({ root }: { root: TaskNode }) {
  return (
    <ul className="space-y-1 font-mono text-xs text-ink">
      <TaskNodeView node={root} depth={0} />
    </ul>
  );
}

function TaskNodeView({ node, depth }: { node: TaskNode; depth: number }) {
  return (
    <li>
      <div className="flex items-center gap-2" style={{ paddingLeft: depth * 16 }}>
        <span className={`h-2 w-2 rounded-full ${STATUS_DOT[node.status]}`} />
        <span className="text-ink">{node.agent}</span>
        {node.tool && <span className="text-ink-tertiary">· {node.tool}</span>}
        {node.elapsedMs != null && <span className="text-ink-tertiary">· {node.elapsedMs}ms</span>}
      </div>
      {node.children?.map((child) => (
        <TaskNodeView key={child.id} node={child} depth={depth + 1} />
      ))}
    </li>
  );
}
