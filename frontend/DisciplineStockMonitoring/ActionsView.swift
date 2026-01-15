import SwiftUI

struct ActionsView: View {
    @StateObject private var viewModel = ActionsViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView()
                } else if let errorMessage = viewModel.errorMessage {
                    Text(errorMessage)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                } else if viewModel.actions.isEmpty {
                    VStack(spacing: 12) {
                        Image(systemName: "hand.raised")
                            .font(.system(size: 44))
                            .foregroundColor(.secondary)
                        Text("No actions allowed")
                            .font(.headline)
                        Text("Staying disciplined is a decision.")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.top, 60)
                } else {
                    List {
                        Section {
                            ForEach(viewModel.actions) { action in
                                NavigationLink {
                                    ActionDetailView(action: action)
                                } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text("\(action.ticker) • \(action.action)")
                                            .font(.headline)
                                        Text(action.trigger)
                                            .font(.subheadline)
                                            .foregroundColor(.secondary)
                                        Text("Triggered \(action.timeSinceTrigger) ago")
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                    }
                                }
                            }
                        } header: {
                            Text("Allowed Actions")
                        }
                    }
                    .refreshable {
                        await viewModel.load()
                    }
                }
            }
            .navigationTitle("Actions")
            .task {
                await viewModel.load()
            }
        }
    }
}

private struct ActionDetailView: View {
    let action: AllowedAction

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("\(action.ticker) \(action.action)")
                .font(.title2.weight(.semibold))
            Text("Triggered by: \(action.trigger)")
                .foregroundColor(.secondary)
            Text("Price snapshot: 0")
                .foregroundColor(.secondary)

            Button("Execute") {}
                .buttonStyle(.borderedProminent)

            Button("Dismiss") {}
                .buttonStyle(.bordered)

            Button("Override (Later)") {}
                .buttonStyle(.bordered)
                .tint(.secondary)
                .disabled(true)
        }
        .padding()
        .navigationTitle("Action Detail")
        .navigationBarTitleDisplayMode(.inline)
    }
}

#Preview {
    ActionsView()
}
