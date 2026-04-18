import SwiftUI

struct ActivityView: View {
    @State private var surfaces: [AxisAPI.Surface] = []
    @State private var loading = true
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    ProgressView("Loading…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let error {
                    VStack(spacing: AxisSpacing.tight) {
                        Text("Couldn't load activity")
                            .font(.headline)
                            .foregroundStyle(AxisColors.ink)
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(AxisColors.inkTertiary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if surfaces.isEmpty {
                    VStack(spacing: AxisSpacing.tight) {
                        Text("No signals yet")
                            .font(.headline)
                            .foregroundStyle(AxisColors.ink)
                        Text("Connect tools on the web to start receiving proactive surfaces.")
                            .font(.caption)
                            .foregroundStyle(AxisColors.inkTertiary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, AxisSpacing.loose)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(surfaces) { s in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(s.signal_type.replacingOccurrences(of: "_", with: " "))
                                .font(.caption)
                                .foregroundStyle(AxisColors.brand)
                            Text(s.title)
                                .font(.body)
                                .foregroundStyle(AxisColors.ink)
                            if let snippet = s.context_snippet {
                                Text(snippet)
                                    .font(.caption)
                                    .foregroundStyle(AxisColors.inkTertiary)
                            }
                        }
                        .padding(.vertical, 4)
                        .listRowBackground(AxisColors.raised)
                    }
                    .listStyle(.plain)
                }
            }
            .background(AxisColors.canvas)
            .navigationTitle("Activity")
            .refreshable { await load() }
            .task { await load() }
        }
    }

    @MainActor
    private func load() async {
        loading = true
        error = nil
        do {
            surfaces = try await AxisAPI.shared.feed()
        } catch {
            self.error = "\(error)"
        }
        loading = false
    }
}
