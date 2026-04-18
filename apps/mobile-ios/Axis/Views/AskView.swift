import SwiftUI

struct AskView: View {
    @State private var prompt = ""
    @State private var running = false
    @State private var lastOutput: String?
    @State private var error: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: AxisSpacing.loose) {
                if let lastOutput {
                    ScrollView {
                        VStack(alignment: .leading, spacing: AxisSpacing.tight) {
                            Text("Last result")
                                .font(.caption)
                                .foregroundStyle(AxisColors.inkTertiary)
                            Text(lastOutput)
                                .font(.body)
                                .foregroundStyle(AxisColors.ink)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(AxisSpacing.loose)
                                .background(AxisColors.raised)
                                .cornerRadius(AxisRadius.card)
                        }
                        .padding(.horizontal, AxisSpacing.loose)
                    }
                } else {
                    Spacer()
                    Text("Ask Axis to do something across your connected tools.")
                        .font(.callout)
                        .foregroundStyle(AxisColors.inkTertiary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, AxisSpacing.loose)
                    Spacer()
                }

                if let error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(AxisColors.danger)
                        .padding(.horizontal, AxisSpacing.loose)
                }

                HStack(spacing: AxisSpacing.tight) {
                    TextField("What do you need?", text: $prompt, axis: .vertical)
                        .textFieldStyle(.plain)
                        .lineLimit(1...4)
                        .padding(AxisSpacing.base)
                        .background(AxisColors.raised)
                        .cornerRadius(AxisRadius.card)
                        .overlay(
                            RoundedRectangle(cornerRadius: AxisRadius.card)
                                .strokeBorder(AxisColors.edge, lineWidth: 1)
                        )
                    Button {
                        Task { await run() }
                    } label: {
                        Text(running ? "…" : "Run")
                            .font(.subheadline.bold())
                            .foregroundStyle(.white)
                            .padding(.vertical, AxisSpacing.base)
                            .padding(.horizontal, AxisSpacing.loose)
                            .background(AxisColors.brand)
                            .cornerRadius(AxisRadius.card)
                    }
                    .disabled(running || prompt.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                .padding(.horizontal, AxisSpacing.loose)
                .padding(.bottom, AxisSpacing.loose)
            }
            .background(AxisColors.canvas)
            .navigationTitle("Ask")
        }
    }

    @MainActor
    private func run() async {
        error = nil
        running = true
        defer { running = false }
        do {
            let res = try await AxisAPI.shared.runAgent(prompt: prompt)
            lastOutput = res.output
            prompt = ""
        } catch {
            self.error = "\(error)"
        }
    }
}
