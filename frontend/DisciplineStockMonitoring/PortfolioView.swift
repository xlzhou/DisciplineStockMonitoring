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
                                        },
                                        onUpdatePosition: { id, avg, qty in
                                            await viewModel.updatePosition(id: id, avgEntryPrice: avg, positionQty: qty)
                                        }
                                    )
                                } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(stock.ticker)
                                            .font(.headline)
                                        Text(priceText(for: stock.price))
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                        unrealizedText(for: stock)
                                            .font(.caption)
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
            .onChange(of: showingAddStock) {
                if !showingAddStock {
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

private func unrealizedText(for stock: PortfolioStock) -> Text {
    guard let price = stock.price,
          let avg = stock.avgEntryPrice,
          let qty = stock.positionQty,
          qty > 0,
          avg > 0
    else {
        return Text("Unrealized: —").foregroundColor(.secondary)
    }

    let pnl = (price - avg) * Double(qty)
    let pct = (price - avg) / avg * 100
    let sign = pnl >= 0 ? "+" : ""
    let text = String(format: "Unrealized: %@%.2f (%.2f%%)", sign, pnl, pct)
    let color: Color = pnl > 0 ? .green : (pnl < 0 ? .red : .secondary)
    return Text(text).foregroundColor(color)
}

private struct StockDetailView: View {
    let stock: PortfolioStock
    let onArchive: (Int) async -> String?
    let onUpdatePosition: (Int, Double?, Int?) async -> String?
    @State private var isArchiving = false
    @State private var archiveError: String?
    @Environment(\.dismiss) private var dismiss
    @State private var avgEntryInput: String = ""
    @State private var qtyInput: String = ""
    @State private var saveMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                detailCard(title: "Identity", lines: [
                    "Ticker: \(stock.ticker)",
                    "Market: US"
                ])

                detailCard(title: "Position State", lines: [
                    "Status: \(stock.positionState)",
                    "Avg Entry: \(formattedPrice(stock.avgEntryPrice))",
                    "Quantity: \(stock.positionQty.map(String.init) ?? "—")"
                ])

                detailCard(title: "Rule Summary", lines: [
                    "Entry: MA trend confirmation",
                    "Exit: Stop-loss + take profit",
                    "Risk: Daily loss limit"
                ])

                HStack(spacing: 12) {
                    NavigationLink("Edit Rules") {
                        RuleEditorView(stockId: stock.id, ticker: stock.ticker)
                    }
                    .buttonStyle(.borderedProminent)

                    Button("Audit Log") {}
                        .buttonStyle(.bordered)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Update Position")
                        .font(.headline)
                    HStack(spacing: 12) {
                        Text("Avg entry price")
                            .frame(width: 130, alignment: .leading)
                        TextField("e.g. 135.50", text: $avgEntryInput)
                            .textFieldStyle(.roundedBorder)
                            .keyboardType(.decimalPad)
                    }
                    HStack(spacing: 12) {
                        Text("Quantity")
                            .frame(width: 130, alignment: .leading)
                        TextField("e.g. 100", text: $qtyInput)
                            .textFieldStyle(.roundedBorder)
                            .keyboardType(.numberPad)
                    }
                    if let saveMessage {
                        Text(saveMessage)
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                    Button("Save Position") {
                        Task { @MainActor in
                            let avg = Double(avgEntryInput)
                            let qty = Int(qtyInput)
                            saveMessage = await onUpdatePosition(stock.id, avg, qty)
                        }
                    }
                    .buttonStyle(.bordered)
                }
                .padding(16)
                .background(Color(.secondarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

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
        .onAppear {
            if avgEntryInput.isEmpty, let avg = stock.avgEntryPrice {
                avgEntryInput = String(format: "%.2f", avg)
            }
            if qtyInput.isEmpty, let qty = stock.positionQty {
                qtyInput = String(qty)
            }
        }
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

    private func formattedPrice(_ value: Double?) -> String {
        guard let value else {
            return "—"
        }
        return String(format: "%.2f", value)
    }
}

#Preview {
    PortfolioView()
}
