import Foundation
import Combine

@MainActor
final class StatusViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var statuses: [StockStatus] = []

    private let apiClient: APIClient
    private var priceRefreshTask: Task<Void, Never>?
    private var isRefreshingPrices = false
    private var lastPriceFetch: Date?

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient ?? APIClient(baseURL: AppConfig.apiBaseURL)
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let stocks = try await apiClient.fetchStocks()
            let visible = stocks.filter { $0.status.lowercased() != "archived" }
            statuses = visible.map { stock in
                StockStatus(
                    id: stock.id,
                    ticker: stock.ticker,
                    state: stock.status == "archived" ? "ARCHIVED" : "BLOCKED",
                    reason: "No decision available",
                    isActionAllowed: false,
                    price: nil
                )
            }
        } catch {
            errorMessage = "Failed to load status: \(error.localizedDescription)"
        }
        isLoading = false
        priceRefreshTask?.cancel()
        priceRefreshTask = Task {
            await refreshPrices(retries: 1, delaySeconds: 4)
        }
    }

    func refreshPrices(retries: Int, delaySeconds: UInt64) async {
        guard !isRefreshingPrices else { return }
        let now = Date()
        if let last = lastPriceFetch, now.timeIntervalSince(last) < 5 {
            return
        }
        lastPriceFetch = now
        isRefreshingPrices = true
        do {
            let prices = try await apiClient.fetchStockPrices()
            let lookup = Dictionary(uniqueKeysWithValues: prices.map { ($0.id, $0.price) })
            statuses = statuses.map { status in
                StockStatus(
                    id: status.id,
                    ticker: status.ticker,
                    state: status.state,
                    reason: status.reason,
                    isActionAllowed: status.isActionAllowed,
                    price: lookup[status.id] ?? status.price
                )
            }
            if retries > 0 && statuses.contains(where: { $0.price == nil }) {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                isRefreshingPrices = false
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
                return
            }
        } catch {
            errorMessage = "Price refresh failed: \(error.localizedDescription)"
            if retries > 0 {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                isRefreshingPrices = false
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
                return
            }
        }
        isRefreshingPrices = false
    }
}

@MainActor
final class PortfolioViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var stocks: [PortfolioStock] = []

    private let apiClient: APIClient
    private var priceRefreshTask: Task<Void, Never>?
    private var isRefreshingPrices = false
    private var lastPriceFetch: Date?

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient ?? APIClient(baseURL: AppConfig.apiBaseURL)
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let results = try await apiClient.fetchStocks()
            let visible = results.filter { $0.status.lowercased() != "archived" }
            var enriched: [PortfolioStock] = []
            for stock in visible {
                var strategy = "Unknown"
                var completeness = "Incomplete"
                do {
                    let plans = try await apiClient.fetchRulePlans(stockId: stock.id)
                    if let active = plans.first(where: { $0.isActive }) ?? plans.sorted(by: { $0.version > $1.version }).first {
                        completeness = "Complete"
                        if let strategyValue = active.rules["strategy_type"] as? String, !strategyValue.isEmpty {
                            strategy = strategyValue.capitalized
                        }
                    }
                } catch {
                    completeness = "Unknown"
                }

                enriched.append(
                    PortfolioStock(
                        id: stock.id,
                        ticker: stock.ticker,
                        strategy: strategy,
                        positionState: stock.positionState.capitalized,
                        ruleCompleteness: completeness,
                        price: nil,
                        avgEntryPrice: stock.avgEntryPrice,
                        positionQty: stock.positionQty
                    )
                )
            }
            stocks = enriched
        } catch {
            errorMessage = "Failed to load portfolio: \(error.localizedDescription)"
        }
        isLoading = false
        priceRefreshTask?.cancel()
        priceRefreshTask = Task {
            await refreshPrices(retries: 1, delaySeconds: 4)
        }
    }

    func clearError() {
        errorMessage = nil
    }

    func addStock(ticker: String, market: String, currency: String, positionState: String) async -> String? {
        isLoading = true
        errorMessage = nil
        do {
            let normalizedTicker = normalizeTicker(ticker, market: market)
            if market.uppercased() == "US" {
                let validation = try await apiClient.validateTicker(normalizedTicker, market: market)
                if validation.status == "unverified" {
                    errorMessage = nil
                } else if !validation.valid {
                    errorMessage = "Ticker not found"
                    isLoading = false
                    return errorMessage
                }
            }
            let payload = StockCreateRequest(
                ticker: normalizedTicker,
                market: market,
                currency: currency,
                status: "active",
                positionState: positionState,
                avgEntryPrice: nil,
                positionQty: nil
            )
            _ = try await apiClient.createStock(payload)
            await load()
            return nil
        } catch {
            errorMessage = "Failed to add stock"
            isLoading = false
            return errorMessage
        }
    }

    func archiveStock(id: Int) async -> String? {
        isLoading = true
        errorMessage = nil
        do {
            _ = try await apiClient.archiveStock(id: id)
            await load()
            return nil
        } catch {
            errorMessage = "Failed to archive stock"
            isLoading = false
            return errorMessage
        }
    }

    func updatePosition(id: Int, avgEntryPrice: Double?, positionQty: Int?) async -> String? {
        isLoading = true
        errorMessage = nil
        do {
            var payload: [String: Any] = [:]
            if let avgEntryPrice {
                payload["avg_entry_price"] = avgEntryPrice
            }
            if let positionQty {
                payload["position_qty"] = positionQty
                payload["position_state"] = positionQty > 0 ? "holding" : "flat"
            }
            _ = try await apiClient.updateStock(id: id, payload: payload)
            await load()
            return nil
        } catch {
            errorMessage = "Failed to update position"
            isLoading = false
            return errorMessage
        }
    }

    private func normalizeTicker(_ ticker: String, market: String) -> String {
        let trimmed = ticker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if market.uppercased() == "HK" {
            let digitsOnly = trimmed.allSatisfy { $0.isNumber }
            if digitsOnly && trimmed.count == 5 {
                return "\(trimmed).HK"
            }
        }
        return trimmed
    }

    func refreshPrices(retries: Int, delaySeconds: UInt64) async {
        guard !isRefreshingPrices else { return }
        let now = Date()
        if let last = lastPriceFetch, now.timeIntervalSince(last) < 5 {
            return
        }
        lastPriceFetch = now
        isRefreshingPrices = true
        do {
            let prices = try await apiClient.fetchStockPrices()
            let lookup = Dictionary(uniqueKeysWithValues: prices.map { ($0.id, $0.price) })
            stocks = stocks.map { stock in
                PortfolioStock(
                    id: stock.id,
                    ticker: stock.ticker,
                    strategy: stock.strategy,
                    positionState: stock.positionState,
                    ruleCompleteness: stock.ruleCompleteness,
                    price: lookup[stock.id] ?? stock.price,
                    avgEntryPrice: stock.avgEntryPrice,
                    positionQty: stock.positionQty
                )
            }
            if retries > 0 && stocks.contains(where: { $0.price == nil }) {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                isRefreshingPrices = false
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
                return
            }
        } catch {
            errorMessage = "Price refresh failed: \(error.localizedDescription)"
            if retries > 0 {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                isRefreshingPrices = false
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
                return
            }
        }
        isRefreshingPrices = false
    }
}

@MainActor
final class ActionsViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var actions: [AllowedAction] = []

    func load() async {
        isLoading = false
        errorMessage = nil
        actions = []
    }
}

@MainActor
final class ReviewViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var metrics: [ReviewMetric] = []
    @Published private(set) var events: [AuditEvent] = []

    func load() async {
        isLoading = false
        errorMessage = nil
        metrics = []
        events = []
    }
}
