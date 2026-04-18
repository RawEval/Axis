import SwiftUI

struct HistoryView: View {
    var body: some View {
        NavigationStack {
            List {
                Text("History will appear here once you run agent actions.")
                    .font(.caption)
                    .foregroundStyle(AxisColors.inkTertiary)
                    .listRowBackground(AxisColors.raised)
            }
            .listStyle(.plain)
            .background(AxisColors.canvas)
            .navigationTitle("History")
        }
    }
}
