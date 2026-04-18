package com.raweval.axis

/**
 * Shared client for calling the Axis backend. Platform-specific HTTP
 * clients are injected via expect/actual declarations.
 *
 * Both iOS and Android consume this — the platform layer supplies the
 * network implementation while this module owns URL paths + request shapes.
 */
expect class HttpClient() {
    suspend fun get(path: String, headers: Map<String, String> = emptyMap()): String
    suspend fun post(path: String, body: String, headers: Map<String, String> = emptyMap()): String
    suspend fun delete(path: String, headers: Map<String, String> = emptyMap()): String
}

class AxisClient(
    private val baseUrl: String,
    private val http: HttpClient,
    private val tokenProvider: () -> String? = { null },
    private val projectProvider: () -> String? = { null },
) {
    private fun authHeaders(): Map<String, String> {
        val h = mutableMapOf("Content-Type" to "application/json")
        tokenProvider()?.let { h["Authorization"] = "Bearer $it" }
        projectProvider()?.let { h["X-Axis-Project"] = it }
        return h
    }

    suspend fun healthz(): Boolean = try { http.get("$baseUrl/healthz"); true } catch (_: Exception) { false }

    suspend fun login(email: String, password: String): String =
        http.post("$baseUrl/auth/login", """{"email":"$email","password":"$password"}""")

    suspend fun me(): String = http.get("$baseUrl/auth/me", authHeaders())
    suspend fun feed(): String = http.get("$baseUrl/feed", authHeaders())
    suspend fun activity(source: String? = null): String {
        val qs = if (source != null) "?source=$source" else ""
        return http.get("$baseUrl/activity$qs", authHeaders())
    }
    suspend fun connectors(): String = http.get("$baseUrl/connectors", authHeaders())
    suspend fun runPrompt(prompt: String): String =
        http.post("$baseUrl/agent/run", """{"prompt":"${prompt.replace("\"", "\\\"")}"}""", authHeaders())

    suspend fun memorySearch(query: String, tier: String? = null): String =
        http.post("$baseUrl/memory/search",
            """{"query":"$query"${if (tier != null) ""","tier":"$tier"""" else ""}}""", authHeaders())

    suspend fun memoryStats(): String = http.get("$baseUrl/memory/stats", authHeaders())
    suspend fun evalScores(limit: Int = 50): String = http.get("$baseUrl/eval/scores?limit=$limit", authHeaders())

    suspend fun submitCorrection(actionId: String, type: String, note: String? = null): String {
        val noteJson = if (note != null) ""","note":"$note"""" else ""
        return http.post("$baseUrl/eval/corrections",
            """{"action_id":"$actionId","correction_type":"$type"$noteJson}""", authHeaders())
    }
}
