import SwiftUI

struct StatusView: View {
    @StateObject private var viewModel = StatusViewModel()

    private var globalStatus: String {
        let allowedCount = viewModel.statuses.filter { $0.isActionAllowed }.count
        if allowedCount == 0 {
            return "No action required"
        }
        return "\(allowedCount) action allowed"
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    statusBanner

                    if viewModel.isLoading {
                        ProgressView()
                    } else if let errorMessage = viewModel.errorMessage {
                        Text(errorMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    } else {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Per-Stock Status")
                                .font(.headline)

                            ForEach(viewModel.statuses) { status in
                                StatusRow(status: status)
                            }
                        }
                        .padding(16)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    }
                }
                .padding()
            }
            .refreshable {
                await viewModel.load()
            }
            .navigationTitle("Status")
            .task {
                await viewModel.load()
            }
        }
    }

    private var statusBanner: some View {
        HStack {
            VStack(alignment: .leading, spacing: 6) {
                Text(globalStatus)
                    .font(.title2.weight(.semibold))
                Text("Open the app, decide, close it.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            Spacer()
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 32))
                .foregroundColor(.accentColor)
        }
        .padding(20)
        .background(Color(.systemBackground))
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(Color(.separator), lineWidth: 1)
        )
    }
}

private struct StatusRow: View {
    let status: StockStatus

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(status.ticker)
                    .font(.headline)
                Text(priceText)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text(status.state)
                    .font(.subheadline.weight(.semibold))
                    .foregroundColor(status.isActionAllowed ? .green : .secondary)
                Text(status.reason)
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            Image(systemName: status.isActionAllowed ? "checkmark.circle.fill" : "pause.circle")
                .foregroundColor(status.isActionAllowed ? .green : .secondary)
        }
        .padding(12)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var priceText: String {
        guard let price = status.price else {
            return "Price: —"
        }
        return String(format: "Price: %.2f", price)
    }
}

#Preview {
    StatusView()
}
