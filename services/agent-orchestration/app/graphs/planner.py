"""LangGraph planner for Axis agent runs — supervisor + tool-use loop.

Topology:

    START → route_project → supervise → END

``supervise`` is the real agent. It runs a Claude tool-use loop:

    1. Call Claude with the user prompt + registered capabilities as tools.
    2. If Claude returns stop_reason=='tool_use', dispatch every tool_use
       block to its Capability, collect the results, append tool_result
       blocks back into the message history, and loop.
    3. If stop_reason=='end_turn', extract the final text and all collected
       citations, and return.
    4. Hard cap: 5 iterations (spec §6.7 "max 5 concurrent sub-agents" applied
       sequentially for Phase 2 — will fan out in Phase 3).

Stub mode (no ANTHROPIC_API_KEY): we still exercise one capability call
deterministically so the rest of the pipeline (citations → rich history →
eval) gets real rows to work with. This lets the UI render a non-trivial
response without any real provider credentials.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict

from axis_common import get_logger
from langgraph.graph import END, StateGraph

from app.capabilities import get_registry
from app.capabilities.base import CapabilityResult, Citation
from app.clients.anthropic import get_client
from app.clients.eval import fetch_prompt_delta
from app.config import settings
from app.events import publish as publish_event
from app.permissions import check_and_gate

logger = get_logger(__name__)

MAX_ITERATIONS = 5


class AgentState(TypedDict, total=False):
    user_id: str
    prompt: str
    project_ids: list[str]
    project_scope: str
    active_project_id: str | None
    plan: list[dict[str, Any]]
    output: str
    citations: list[dict[str, Any]]
    tokens_used: int
    model: str
    error: str


SYSTEM_PROMPT = """You are Axis, a cross-tool AI agent for startup teams.

You have tools to read the user's connected workspace — Notion pages, their
activity stream across every connected tool, and their memory of past
conversations. Use them proactively when the user's question would benefit
from real data. Don't fabricate facts — call the tools.

When you call a tool, the result comes back as a tool_result content block.
You can then produce your final answer or call another tool.

Response style:
1. Be concise. 2-4 sentences unless the user asks for depth.
2. When you cite data from a tool result, quote or paraphrase briefly. The
   UI highlights the corresponding text and shows a clickable source card.
3. If the user's question cannot be answered with the available tools, say
   so plainly. Don't guess.
4. Never claim to have executed a write action. All writes require user
   confirmation and land in a separate flow.
"""


async def route_project(state: AgentState) -> AgentState:
    scope = state.get("project_scope", "default")
    ids = state.get("project_ids") or []
    if not ids:
        logger.warning("route_project_no_ids", scope=scope)
        return {**state, "active_project_id": None}
    logger.info("route_project", scope=scope, count=len(ids))
    return {**state, "active_project_id": ids[0]}


async def supervise(state: AgentState) -> AgentState:
    """Claude tool-use loop with real capabilities.

    Returns the updated state with `output`, `citations`, `plan`, `tokens_used`.
    """
    user_id = state["user_id"]
    active_project_id = state.get("active_project_id")
    prompt = state["prompt"]

    registry = get_registry()
    tools = registry.anthropic_tools()

    client = get_client()
    if client is None:
        return await _stub_supervise(state, registry)

    # Short-loop correction delta — the user's accumulated behavior
    # instructions, synthesized by eval-engine from recent corrections.
    # Fetched on the critical path with a tight timeout; empty string if
    # eval-engine is unreachable or the user has no corrections yet.
    prompt_delta = await fetch_prompt_delta(user_id)

    # The message history that Claude mutates across iterations.
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": prompt},
    ]
    plan: list[dict[str, Any]] = []
    all_citations: list[dict[str, Any]] = []
    total_tokens = 0

    await publish_event(
        user_id=user_id,
        project_id=active_project_id,
        event_type="task.started",
        payload={"prompt": prompt, "has_delta": bool(prompt_delta)},
    )

    # Build the system block. Base prompt goes first with prompt caching so
    # it stays in the cache across users; the per-user delta is appended as
    # a separate, non-cached block so corrections update instantly.
    system_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    if prompt_delta:
        system_blocks.append(
            {
                "type": "text",
                "text": (
                    "# User-specific behavior delta\n"
                    "Follow these instructions on top of the base rules:\n"
                    f"{prompt_delta}"
                ),
            }
        )

    for iteration in range(MAX_ITERATIONS):
        try:
            resp = await client.messages.create(
                model=settings.anthropic_model_sonnet,
                max_tokens=settings.anthropic_max_tokens,
                temperature=settings.anthropic_temperature,
                system=system_blocks,
                tools=tools,
                messages=messages,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("anthropic_call_failed", error=str(e))
            return {
                **state,
                "output": f"Agent error: {e}",
                "error": str(e),
                "plan": plan,
                "citations": all_citations,
            }

        usage = getattr(resp, "usage", None)
        if usage is not None:
            total_tokens += (usage.input_tokens or 0) + (usage.output_tokens or 0)

        stop_reason = getattr(resp, "stop_reason", None)
        content_blocks = list(resp.content)

        # Append the assistant's turn (including any tool_use blocks) to history.
        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason == "end_turn" or all(
            getattr(b, "type", "") != "tool_use" for b in content_blocks
        ):
            text_parts = [b.text for b in content_blocks if getattr(b, "type", "") == "text"]
            output = "\n".join(text_parts).strip() or "(empty response)"
            plan.append(
                {
                    "step": iteration + 1,
                    "kind": "synthesise",
                    "model": settings.anthropic_model_sonnet,
                    "status": "done",
                }
            )
            await publish_event(
                user_id=user_id,
                project_id=active_project_id,
                event_type="task.completed",
                payload={
                    "output_preview": output[:240],
                    "tokens_used": total_tokens,
                    "plan_len": len(plan),
                    "citations": len(all_citations),
                },
            )
            return {
                **state,
                "output": output,
                "citations": all_citations,
                "plan": plan,
                "tokens_used": total_tokens,
                "model": settings.anthropic_model_sonnet,
            }

        # stop_reason == 'tool_use': dispatch tool_use blocks IN PARALLEL
        # When Claude returns 2+ tool calls, we run them all concurrently
        # via asyncio.gather — cuts multi-tool latency by 2-5x.
        tool_use_blocks = [
            b for b in content_blocks if getattr(b, "type", "") == "tool_use"
        ]

        async def _dispatch_one(block: Any) -> dict[str, Any]:
            """Run one tool_use block through gate → execute → collect."""
            cap = registry.get(block.name)
            if cap is None:
                logger.warning("unknown_capability", name=block.name)
                plan.append({"step": iteration + 1, "kind": "tool_use", "name": block.name, "status": "unknown"})
                return {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": f"unknown capability: {block.name}"}),
                    "is_error": True,
                }

            gate = await check_and_gate(
                user_id=user_id,
                project_id=active_project_id,
                capability=cap,
                inputs=dict(block.input),
            )
            if not gate.granted:
                logger.info("capability_denied", name=block.name, reason=gate.reason)
                plan.append({"step": iteration + 1, "kind": "tool_use", "name": cap.name, "status": "denied", "summary": gate.reason})
                await publish_event(user_id=user_id, project_id=active_project_id, event_type="step.completed", payload={"step": iteration + 1, "name": cap.name, "status": "denied", "reason": gate.reason})
                return {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"error": f"permission denied: {gate.reason}"}),
                    "is_error": True,
                }

            await publish_event(user_id=user_id, project_id=active_project_id, event_type="step.started", payload={"step": iteration + 1, "kind": "tool_use", "name": cap.name, "inputs": dict(block.input)})

            try:
                result: CapabilityResult = await cap(
                    user_id=user_id,
                    project_id=active_project_id,
                    org_id=None,
                    inputs=dict(block.input),
                )
            except Exception as e:  # noqa: BLE001
                logger.error("capability_failed", name=block.name, error=str(e))
                result = CapabilityResult(summary=f"{block.name} failed", content=[], error=str(e))

            await publish_event(user_id=user_id, project_id=active_project_id, event_type="step.completed", payload={"step": iteration + 1, "name": cap.name, "status": "error" if result.is_error else "done", "summary": result.summary, "citations": len(result.citations)})

            all_citations.extend(c.to_dict() for c in result.citations)
            plan.append({"step": iteration + 1, "kind": "tool_use", "name": block.name, "status": "error" if result.is_error else "done", "summary": result.summary})
            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result.to_tool_result(),
                "is_error": result.is_error,
            }

        # Fan out — all tool calls run concurrently (spec §6.7: max 5)
        tool_results = list(await asyncio.gather(
            *[_dispatch_one(b) for b in tool_use_blocks],
            return_exceptions=False,
        ))

        messages.append({"role": "user", "content": tool_results})

    # Ran out of iterations — return what we have with a note
    logger.warning("supervise_max_iterations_hit")
    return {
        **state,
        "output": "I ran out of iterations before finishing. Try a narrower question.",
        "citations": all_citations,
        "plan": plan,
        "tokens_used": total_tokens,
        "model": settings.anthropic_model_sonnet,
    }


async def _stub_supervise(state: AgentState, registry) -> AgentState:
    """Deterministic path when there is no real ANTHROPIC_API_KEY.

    We still walk one capability so the rest of the pipeline (citations,
    rich history, eval) gets real rows to work with. Today we call
    ``activity.query`` over the last day — it returns [] because nothing
    ingests yet, but the call path proves the plumbing.
    """
    user_id = state["user_id"]
    active_project_id = state.get("active_project_id")
    prompt = state["prompt"]

    plan: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    activity_cap = registry.get("activity.query")
    if activity_cap is not None:
        try:
            result = await activity_cap(
                user_id=user_id,
                project_id=active_project_id,
                org_id=None,
                inputs={"since": "today", "source": "all", "limit": 20},
            )
            citations.extend(c.to_dict() for c in result.citations)
            plan.append(
                {
                    "step": 1,
                    "kind": "tool_use",
                    "name": activity_cap.name,
                    "status": "done",
                    "summary": result.summary,
                }
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("stub_capability_failed", error=str(e))

    # Produce a structured stub response that still feels product-like. If
    # the activity query found any events, weave them into the answer with
    # citation spans so the UI renders highlights.
    if citations:
        first = citations[0]
        output = (
            f"Axis is in stub mode (no ANTHROPIC_API_KEY set), but I still "
            f"pulled {len(citations)} activity event(s) from your stream. "
            f"Most recent: {first.get('title') or first.get('excerpt') or 'untitled'}. "
            f"Your prompt was: {prompt}"
        )
    else:
        output = (
            f"Axis is in stub mode (no ANTHROPIC_API_KEY set). Your activity "
            f"stream is empty, so nothing was pulled. Your prompt was: {prompt}"
        )
        plan.append(
            {
                "step": len(plan) + 1,
                "kind": "stub_fallback",
                "name": "synthesise",
                "status": "done",
            }
        )

    return {
        **state,
        "output": output,
        "citations": citations,
        "plan": plan,
        "tokens_used": 0,
        "model": "stub",
    }


def build_planner_graph():
    g: StateGraph = StateGraph(AgentState)
    g.add_node("route_project", route_project)
    g.add_node("supervise", supervise)
    g.set_entry_point("route_project")
    g.add_edge("route_project", "supervise")
    g.add_edge("supervise", END)
    return g.compile()
