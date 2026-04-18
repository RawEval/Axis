import Foundation

/// Minimal Axis API client for the Phase 1 mobile skeleton.
///
/// Responsibilities:
///   - base URL resolution (dev vs prod)
///   - JWT storage in Keychain (Phase 2 — using UserDefaults for now)
///   - X-Axis-Project header injection from the shared store
///   - typed responses for /healthz, /auth/login, /auth/me, /feed, /agent/run
///
/// Everything else is Phase 2 (push, offline cache, streaming).
struct AxisAPI {
    static let shared = AxisAPI()

    let baseURL: URL

    init() {
        // Simulator → localhost; device → your LAN IP
        self.baseURL = URL(string: "http://localhost:8000")!
    }

    // MARK: - Models

    struct LoginResponse: Decodable {
        let access_token: String
        let expires_in: Int
    }

    struct Me: Decodable {
        let id: String
        let email: String
        let name: String?
        let plan: String
    }

    struct Project: Decodable, Identifiable {
        let id: String
        let name: String
        let is_default: Bool
    }

    struct Surface: Decodable, Identifiable {
        let id: String
        let signal_type: String
        let title: String
        let context_snippet: String?
        let confidence_score: Double?
        let created_at: String
    }

    struct ConnectorTile: Decodable, Identifiable {
        var id: String { tool }
        let tool: String
        let status: String
        let health: String?
        let workspace_name: String?
    }

    struct RunResponse: Decodable {
        let action_id: String
        let output: String
        let tokens_used: Int
        let latency_ms: Int
    }

    // MARK: - Token

    func token() -> String? {
        UserDefaults.standard.string(forKey: "axis.token")
    }

    func setToken(_ t: String?) {
        if let t {
            UserDefaults.standard.set(t, forKey: "axis.token")
        } else {
            UserDefaults.standard.removeObject(forKey: "axis.token")
        }
    }

    func activeProject() -> String? {
        UserDefaults.standard.string(forKey: "axis.project")
    }

    struct ActivityEvent: Decodable, Identifiable {
        let id: String
        let source: String
        let event_type: String
        let actor: String?
        let title: String
        let snippet: String?
        let occurred_at: String?
    }

    struct MemoryRow: Decodable, Identifiable {
        let id: String
        let tier: String
        let type: String
        let content: String
        let score: Double
    }

    struct MemoryStats: Decodable {
        let episodic_count: Int
        let semantic_count: Int
        let embedding_provider: String
    }

    // MARK: - Cache
    // Phase 1: UserDefaults-backed JSON cache. Survives app restarts.
    // Phase 2: migrate to Core Data for indexing + larger datasets.

    func cache<T: Encodable>(key: String, data: T) {
        if let json = try? JSONEncoder().encode(data) {
            UserDefaults.standard.set(json, forKey: "axis.cache.\(key)")
        }
    }

    func cached<T: Decodable>(key: String, as _: T.Type) -> T? {
        guard let data = UserDefaults.standard.data(forKey: "axis.cache.\(key)") else { return nil }
        return try? JSONDecoder().decode(T.self, from: data)
    }

    // MARK: - Requests

    func healthz() async -> Bool {
        do {
            let (_, resp) = try await URLSession.shared.data(
                from: baseURL.appending(path: "/healthz"))
            return (resp as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }

    func login(email: String, password: String) async throws -> LoginResponse {
        let body = try JSONSerialization.data(withJSONObject: [
            "email": email, "password": password
        ])
        let req = makeRequest("POST", path: "/auth/login", body: body)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        let decoded = try JSONDecoder().decode(LoginResponse.self, from: data)
        setToken(decoded.access_token)
        return decoded
    }

    func me() async throws -> Me {
        let req = makeRequest("GET", path: "/auth/me")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode(Me.self, from: data)
    }

    func feed() async throws -> [Surface] {
        let req = makeRequest("GET", path: "/feed")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode([Surface].self, from: data)
    }

    func connectors() async throws -> [ConnectorTile] {
        let req = makeRequest("GET", path: "/connectors")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode([ConnectorTile].self, from: data)
    }

    func runAgent(prompt: String) async throws -> RunResponse {
        let body = try JSONSerialization.data(withJSONObject: ["prompt": prompt])
        let req = makeRequest("POST", path: "/agent/run", body: body)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode(RunResponse.self, from: data)
    }

    func activity(source: String? = nil) async throws -> [ActivityEvent] {
        var path = "/activity"
        if let s = source { path += "?source=\(s)" }
        let req = makeRequest("GET", path: path)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        let result = try JSONDecoder().decode([ActivityEvent].self, from: data)
        cache(key: "activity", data: result)
        return result
    }

    func memorySearch(query: String) async throws -> [MemoryRow] {
        let body = try JSONSerialization.data(withJSONObject: ["query": query, "limit": 20])
        let req = makeRequest("POST", path: "/memory/search", body: body)
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode([MemoryRow].self, from: data)
    }

    func memoryStats() async throws -> MemoryStats {
        let req = makeRequest("GET", path: "/memory/stats")
        let (data, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
        return try JSONDecoder().decode(MemoryStats.self, from: data)
    }

    func submitCorrection(actionId: String, type: String, note: String?) async throws {
        var dict: [String: Any] = ["action_id": actionId, "correction_type": type]
        if let n = note { dict["note"] = n }
        let body = try JSONSerialization.data(withJSONObject: dict)
        let req = makeRequest("POST", path: "/eval/corrections", body: body)
        let (_, resp) = try await URLSession.shared.data(for: req)
        try check(resp)
    }

    // MARK: - Helpers

    private func makeRequest(_ method: String, path: String, body: Data? = nil) -> URLRequest {
        var req = URLRequest(url: baseURL.appending(path: path))
        req.httpMethod = method
        req.httpBody = body
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let t = token() {
            req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization")
        }
        if let p = activeProject(), !p.isEmpty {
            req.setValue(p, forHTTPHeaderField: "X-Axis-Project")
        }
        return req
    }

    private func check(_ resp: URLResponse) throws {
        guard let http = resp as? HTTPURLResponse else {
            throw APIError.invalid
        }
        if http.statusCode == 401 {
            setToken(nil)
            throw APIError.unauthorized
        }
        if http.statusCode >= 400 {
            throw APIError.http(status: http.statusCode)
        }
    }

    enum APIError: Error {
        case invalid
        case unauthorized
        case http(status: Int)
    }
}
