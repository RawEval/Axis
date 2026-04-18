# Streaming & Real-Time — SSE + WebSocket topology

**Decision date:** 2026-04-16
**Status:** Design (Phase 2 implementation)
**ADR number:** 008

## Context

Two product behaviors both need real-time backbone:

1. **Live task progress**: "Axis is cloning the repo..." → "searching for 'pricing'..." → "drafting the summary..." — the user should see the agent's moves as they happen, not wait 60 seconds for a terminal answer.
2. **Permission interrupts**: when the agent hits a gated capability, it pauses, the UI pops a modal, the user decides, the agent resumes. The channel carrying the `permission_request` event has to be live.

Phase 1 has an auth'd WebSocket stub at `/ws` but no producer. This doc specifies the full pipeline.

## Decision

Ship **two transports**, chosen by client:

- **WebSocket** for desktop web (richer, bidirectional — user clicks in the UI feed back through the same socket)
- **SSE** (Server-Sent Events) for mobile web and fallback (lighter, unidirectional, firewall-friendly)

Both are authed via JWT in the query string (spec says query-string for WebSocket; SSE same for consistency).

## Architecture

```
  ┌────────────────────────────────────────────────┐
  │                                                │
  │  orchestration  ──▶  Redis pub/sub  ◀── gateway
  │  publishes            channel per user          │
  │  events               axis.events.<user_id>    │
  │                                                │
  └────────┬───────────────────────────┬───────────┘
           │                           │
           ▼                           ▼
     web WebSocket                SSE (mobile)
     (per-user conn)              (per-user conn)
```

- `agent-orchestration` runs the task and publishes events to `axis.events.<user_id>` on Redis.
- `api-gateway` owns the user-facing connections. Each open connection subscribes to the user's Redis channel and forwards matching events.
- Messages are JSON, typed by an `event_type` field (see below).

## Event envelope

```typescript
type AxisEvent =
  | AgentRunStartedEvent
  | StepStartedEvent
  | StepTokenDeltaEvent          // token-by-token streaming
  | ToolCallStartedEvent
  | ToolCallResultEvent
  | PermissionRequestEvent
  | PermissionResolvedEvent
  | StepCompletedEvent
  | AgentRunCompletedEvent
  | AgentRunErrorEvent
  | ActivityEvent                // from the activity stream
  | ProactiveSurfaceEvent;       // §6.3

type EventBase = {
  id: string;                    // ulid
  task_id?: string;
  user_id: string;
  project_id?: string;
  event_type: string;
  timestamp: string;             // iso
};

type StepTokenDeltaEvent = EventBase & {
  event_type: "step.token_delta";
  step_id: string;
  text: string;                  // incremental token chunk
};

type PermissionRequestEvent = EventBase & {
  event_type: "permission.request";
  step_id: string;
  capability: string;
  action: "read" | "write" | "execute";
  context: Record<string, unknown>;
  suggested_lifetime: "session" | "project" | "forever";
};

// ... and so on
```

## Publishing side (agent-orchestration)

Each node in the LangGraph planner writes events as it progresses. A thin wrapper:

```python
# services/agent-orchestration/app/events.py
class EventBus:
    def __init__(self, redis: Redis, user_id: str) -> None:
        self._redis = redis
        self._channel = f"axis.events.{user_id}"

    async def publish(self, event: dict) -> None:
        await self._redis.publish(self._channel, json.dumps(event))
```

Usage inside a node:

```python
async def parse_and_synthesise(state: AgentState) -> AgentState:
    bus = EventBus(redis, state["user_id"])
    await bus.publish({
        "event_type": "step.started",
        "task_id": state["task_id"],
        "step_id": "synthesise",
        "agent_role": "synthesise",
    })
    async for chunk in client.messages.stream(...):
        if chunk.type == "content_block_delta":
            await bus.publish({
                "event_type": "step.token_delta",
                "task_id": state["task_id"],
                "step_id": "synthesise",
                "text": chunk.delta.text,
            })
    await bus.publish({"event_type": "step.completed", ...})
```

## Subscribing side (api-gateway)

The gateway's `/ws` endpoint (already scaffolded) is extended to subscribe to the user's Redis channel and forward events:

```python
@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str | None = Query(default=None)):
    user_id = validate_token(token)  # or close with 1008
    await ws.accept()

    redis = get_redis()
    channel = f"axis.events.{user_id}"

    async with redis.pubsub() as ps:
        await ps.subscribe(channel)
        try:
            while True:
                # Listen to both Redis events and client messages in parallel
                done, pending = await asyncio.wait(
                    [
                        asyncio.create_task(ps.get_message(ignore_subscribe=True, timeout=1)),
                        asyncio.create_task(ws.receive_json()),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in done:
                    result = task.result()
                    if isinstance(result, dict) and result.get("type") == "message":
                        # Redis event → forward to client
                        await ws.send_text(result["data"])
                    else:
                        # Client message (permission decision, cancel, etc.)
                        await handle_client_message(result)
                for task in pending:
                    task.cancel()
        except WebSocketDisconnect:
            return
```

For SSE, the loop is simpler (no client→server channel); clients deliver permission decisions via a plain `POST /permissions/grant`.

## Event ordering and replay

- Each event has a ULID timestamp. Clients can sort on arrival.
- If the connection drops mid-task, clients reconnect and pass `?from=<last_event_id>`. The gateway reads the missed events from a Redis Stream (`axis.events.<user_id>.stream`) and replays them. Retention: 15 minutes or 500 events, whichever is less.
- The pub/sub channel is for live; the stream is for replay.

## Permission interrupts in practice

```
orchestrator pauses task at step 4 (needs connector.gmail.read)
  → bus.publish({type: "permission.request", step_id: "4", capability: "...", context: {...}})
  → gateway forwards to all the user's active connections
  → web shows a modal, user picks "Allow for this project"
  → web sends POST /permissions/grant (HTTP, not socket)
  → gateway persists grant, publishes {type: "permission.resolved", step_id: "4", decision: "granted"}
  → orchestrator has been awaiting a Redis key `axis.awaiting.{task_id}.{step_id}`
  → the grant publisher sets that key; orchestrator wakes up and continues the supervisor loop
```

The `axis.awaiting.*` keys are TTL'd (30 minutes) so a dead task doesn't block a worker forever. If the TTL fires, the task is marked `failed` with reason `permission_timeout`.

## Rate limits on streaming

- Max **1 concurrent WebSocket per user** (cheaper, forces a single-tab UX). Extra connections are rejected 1008.
- Max **5 concurrent agent tasks per user**. A 6th request queues or returns 429 based on plan tier.
- Token-delta events throttled to ~30 per second client-side (the backend publishes everything; the frontend buffers and batches render).

## Failure modes

| Failure | Behavior |
|---|---|
| Redis down | Orchestrator logs, proceeds without publishing. Tasks complete but there's no live view. User sees the final result on refresh. |
| WebSocket drops mid-task | Client reconnects with `?from=<last_id>`, replays from Redis Stream, resumes. |
| Permission grant never arrives | `awaiting` TTL fires after 30min, task marked `failed`, user notified by email. |
| Orchestrator dies mid-task | Task row stays in `running`; a janitor job flips it to `failed` after 10min of no heartbeat. |
| Gateway dies | All active sockets drop. Clients reconnect to another gateway instance and resume from stream. |

## Phase-1 → Phase-2 delta

- Phase 1 has `/ws` with JWT auth. Phase 2 adds the Redis pub/sub subscription and bidirectional message handling.
- Phase 1 has no event bus in orchestration. Phase 2 adds `EventBus` and threads it through every graph node.
- Phase 1 returns the full response at end of task. Phase 2 still does this (for HTTP compat) but simultaneously streams tokens over the socket.

## What this unlocks

- Live task tree in the web UI (spec §8.1 "Task Tree" component is already scaffolded in `apps/web/components/task-tree.tsx`)
- Permission modals (`permissions-model.md`)
- Token-by-token rendering of the agent's answer
- Proactive surfaces pushed to the feed in real-time
- Notifications that can be dismissed in-app before the push arrives

## See also

- `agentic-architecture.md`
- `permissions-model.md`
- `activity-feed.md`
- `prompt-flow.md`
