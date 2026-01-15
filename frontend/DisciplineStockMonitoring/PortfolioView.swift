import SwiftUI

struct PortfolioView: View {
    @StateObject private var viewModel = PortfolioViewModel()
    @State private var showingAddStock = false

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading {
                    ProgressView()
                } else if viewModel.stocks.isEmpty {
                    Text(viewModel.errorMessage ?? "No stocks yet")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                } else {
                    List {
                        if let errorMessage = viewModel.errorMessage {
                            Section {
                                Text(errorMessage)
                                    .font(.footnote)
                                    .foregroundColor(.secondary)
                            }
                        }
                        Section {
                            ForEach(viewModel.stocks) { stock in
                                NavigationLink {
                                    StockDetailView(
                                        stock: stock,
                                        onArchive: { id in
                                            await viewModel.archiveStock(id: id)
                                        }
                                    )
                                } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(stock.ticker)
                                            .font(.headline)
                                        Text(priceText(for: stock.price))
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                        Text("\(stock.strategy) • \(stock.positionState)")
                                            .font(.subheadline)
                                            .foregroundColor(.secondary)
                                        Text("Rules: \(stock.ruleCompleteness)")
                                            .font(.caption)
                                            .foregroundColor(stock.ruleCompleteness == "Complete" ? .green : .orange)
                                    }
                                }
                            }
                        } header: {
                            Text("Portfolio")
                        }
                    }
                    .refreshable {
                        await viewModel.load()
                    }
                }
            }
            .navigationTitle("Portfolio")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Add Stock") {
                        showingAddStock = true
                    }
                }
            }
            .task {
                await viewModel.load()
            }
            .sheet(isPresented: $showingAddStock, onDismiss: {
                viewModel.clearError()
            }) {
                AddStockView { ticker, market, currency, positionState in
                    await viewModel.addStock(
                        ticker: ticker,
                        market: market,
                        currency: currency,
                        positionState: positionState
                    )
                }
            }
            .onChange(of: showingAddStock) { isShowing in
                if !isShowing {
                    Task {
                        await viewModel.load()
                    }
                }
            }
        }
    }
}

private func priceText(for price: Double?) -> String {
    guard let price else {
        return "Price: —"
    }
    return String(format: "Price: %.2f", price)
}

private struct StockDetailView: View {
    let stock: PortfolioStock
    let onArchive: (Int) async -> String?
    @State private var isArchiving = false
    @State private var archiveError: String?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                detailCard(title: "Identity", lines: [
                    "Ticker: \(stock.ticker)",
                    "Market: US"
                ])

                detailCard(title: "Position State", lines: [
                    "Status: \(stock.positionState)",
                    "Avg Entry: 0",
                    "Days Held: 0"
                ])

                detailCard(title: "Rule Summary", lines: [
                    "Entry: MA trend confirmation",
                    "Exit: Stop-loss + take profit",
                    "Risk: Daily loss limit"
                ])

                HStack(spacing: 12) {
                    NavigationLink("Edit Rules") {
                        RuleEditorView()
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Audit Log") {}
                        .buttonStyle(.bordered)
                }

                if let archiveError {
                    Text(archiveError)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }

                Button("Archive Stock", role: .destructive) {
                    Task { @MainActor in
                        isArchiving = true
                        archiveError = await onArchive(stock.id)
                        isArchiving = false
                        if archiveError == nil {
                            dismiss()
                        }
                    }
                }
                .buttonStyle(.bordered)
                .disabled(isArchiving)
            }
            .padding()
        }
        .navigationTitle(stock.ticker)
        .navigationBarTitleDisplayMode(.inline)
    }

    private func detailCard(title: String, lines: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            ForEach(lines, id: \.self) { line in
                Text(line)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .padding(16)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

#Preview {
    PortfolioView()
}
