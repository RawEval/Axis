package com.raweval.axis.models

/**
 * Shared data classes consumed by both iOS (via KMM framework) and Android.
 * Mirror the Pydantic models in services/api-gateway + agent-orchestration.
 *
 * Each class uses kotlinx.serialization annotations so they decode from
 * the JSON the gateway returns. iOS consumes these via the KMM framework
 * export — Swift sees them as native structs.
 */

import kotlinx.serialization.Serializable

// ---------- Auth ----------

@Serializable
data class LoginResponse(
    val access_token: String,
    val expires_in: Int,
)

@Serializable
data class Me(
    val id: String,
    val email: String,
    val name: String? = null,
    val plan: String = "free",
    val created_at: String? = null,
)

// ---------- Projects ----------

@Serializable
data class Project(
    val id: String,
    val name: String,
    val is_default: Boolean = false,
)

// ---------- Feed ----------

@Serializable
data class Surface(
    val id: String,
    val signal_type: String,
    val title: String,
    val context_snippet: String? = null,
    val confidence_score: Double? = null,
    val status: String = "pending",
    val created_at: String,
)

// ---------- Activity ----------

@Serializable
data class ActivityEvent(
    val id: String,
    val source: String,
    val event_type: String,
    val actor: String? = null,
    val title: String,
    val snippet: String? = null,
    val occurred_at: String? = null,
    val project_id: String? = null,
)

// ---------- Agent ----------

@Serializable
data class Citation(
    val id: String? = null,
    val source_type: String,
    val provider: String? = null,
    val ref_id: String? = null,
    val url: String? = null,
    val title: String? = null,
    val actor: String? = null,
    val excerpt: String? = null,
    val occurred_at: String? = null,
)

@Serializable
data class PlanStep(
    val step: Int = 0,
    val kind: String = "",
    val name: String? = null,
    val model: String? = null,
    val status: String = "pending",
    val summary: String? = null,
)

@Serializable
data class RunResponse(
    val action_id: String,
    val task_id: String? = null,
    val message_id: String? = null,
    val project_id: String? = null,
    val output: String,
    val plan: List<PlanStep> = emptyList(),
    val citations: List<Citation> = emptyList(),
    val tokens_used: Int = 0,
    val latency_ms: Int = 0,
)

// ---------- Connectors ----------

@Serializable
data class ConnectorTile(
    val tool: String,
    val status: String,
    val health: String? = null,
    val workspace_name: String? = null,
)

// ---------- Memory ----------

@Serializable
data class MemoryRow(
    val id: String,
    val tier: String,
    val type: String,
    val content: String,
    val score: Double = 0.0,
)

@Serializable
data class MemoryStats(
    val user_id: String,
    val episodic_count: Int = 0,
    val semantic_count: Int = 0,
    val embedding_provider: String = "unknown",
)

// ---------- Eval ----------

@Serializable
data class EvalScore(
    val dimension: String,
    val score: Int,
    val reason: String = "",
)

@Serializable
data class EvalResult(
    val id: String,
    val action_id: String,
    val rubric_type: String,
    val composite_score: Double? = null,
    val flagged: Boolean = false,
    val scores: List<EvalScore> = emptyList(),
    val created_at: String,
)

// ---------- Live Events ----------

@Serializable
data class LiveEvent(
    val type: String,
    val user_id: String? = null,
    val project_id: String? = null,
    val action_id: String? = null,
    val ts: String? = null,
)
