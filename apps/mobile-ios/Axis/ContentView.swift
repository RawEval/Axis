import SwiftUI

struct ContentView: View {
    @State private var healthy = false

    var body: some View {
        TabView {
            ActivityView()
                .tabItem { Label("Activity", systemImage: "list.bullet.rectangle") }
            AskView()
                .tabItem { Label("Ask", systemImage: "text.bubble") }
            HistoryView()
                .tabItem { Label("History", systemImage: "clock.arrow.circlepath") }
            ConnectionsView()
                .tabItem { Label("Tools", systemImage: "link") }
        }
        .accentColor(AxisColors.brand)
        .background(AxisColors.canvas)
        .task {
            healthy = await AxisAPI.shared.healthz()
        }
    }
}

#Preview {
    ContentView()
}
