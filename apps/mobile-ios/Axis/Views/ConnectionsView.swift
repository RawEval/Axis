import SwiftUI

struct ConnectionsView: View {
    @State private var tiles: [AxisAPI.ConnectorTile] = []
    @State private var loading = true

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if tiles.isEmpty {
                    Text("No connectors available. Create a project on the web to get started.")
                        .font(.caption)
                        .foregroundStyle(AxisColors.inkTertiary)
                        .multilineTextAlignment(.center)
                        .padding(AxisSpacing.loose)
                } else {
                    List(tiles) { tile in
                        HStack(alignment: .center) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(tile.tool.capitalized)
                                    .font(.body)
                                    .foregroundStyle(AxisColors.ink)
                                if let workspace = tile.workspace_name {
                                    Text(workspace)
                                        .font(.caption)
                                        .foregroundStyle(AxisColors.inkTertiary)
                                }
                            }
                            Spacer()
                            Text(tile.status)
                                .font(.caption)
                                .foregroundStyle(
                                    tile.status == "connected"
                                    ? AxisColors.success
                                    : AxisColors.inkTertiary
                                )
                        }
                        .listRowBackground(AxisColors.raised)
                    }
                    .listStyle(.plain)
                }
            }
            .background(AxisColors.canvas)
            .navigationTitle("Tools")
            .task {
                do {
                    tiles = try await AxisAPI.shared.connectors()
                } catch {
                    tiles = []
                }
                loading = false
            }
        }
    }
}
