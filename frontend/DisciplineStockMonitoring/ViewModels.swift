import Foundation
import Combine

@MainActor
final class StatusViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var statuses: [StockStatus] = []

    private let apiClient: APIClient

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
        Task {
            await refreshPrices(retries: 2, delaySeconds: 4)
        }
    }

    func refreshPrices(retries: Int, delaySeconds: UInt64) async {
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
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
            }
        } catch {
            errorMessage = "Price refresh failed: \(error.localizedDescription)"
            if retries > 0 {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
            }
        }
    }
}

@MainActor
final class PortfolioViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published private(set) var stocks: [PortfolioStock] = []

    private let apiClient: APIClient

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient ?? APIClient(baseURL: AppConfig.apiBaseURL)
    }

    func load() async {
        isLoading = true
        errorMessage = nil
        do {
            let results = try await apiClient.fetchStocks()
            let visible = results.filter { $0.status.lowercased() != "archived" }
            stocks = visible.map { stock in
                PortfolioStock(
                    id: stock.id,
                    ticker: stock.ticker,
                    strategy: "Unknown",
                    positionState: stock.positionState.capitalized,
                    ruleCompleteness: "Unknown",
                    price: nil
                )
            }
        } catch {
            errorMessage = "Failed to load portfolio: \(error.localizedDescription)"
        }
        isLoading = false
        Task {
            await refreshPrices(retries: 2, delaySeconds: 4)
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
                positionState: positionState
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
                    price: lookup[stock.id] ?? stock.price
                )
            }
            if retries > 0 && stocks.contains(where: { $0.price == nil }) {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
            }
        } catch {
            errorMessage = "Price refresh failed: \(error.localizedDescription)"
            if retries > 0 {
                try? await Task.sleep(nanoseconds: delaySeconds * 1_000_000_000)
                await refreshPrices(retries: retries - 1, delaySeconds: delaySeconds)
            }
        }
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
