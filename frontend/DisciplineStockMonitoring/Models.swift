import Foundation

struct StockStatus: Identifiable {
    let id: Int
    let ticker: String
    let state: String
    let reason: String
    let isActionAllowed: Bool
    let price: Double?
}

struct PortfolioStock: Identifiable {
    let id: Int
    let ticker: String
    let strategy: String
    let positionState: String
    let ruleCompleteness: String
    let price: Double?
    let avgEntryPrice: Double?
    let positionQty: Int?
}

struct AllowedAction: Identifiable {
    let id = UUID()
    let ticker: String
    let action: String
    let trigger: String
    let timeSinceTrigger: String
}

struct AuditEvent: Identifiable {
    let id = UUID()
    let timestamp: String
    let eventType: String
    let detail: String
}

struct ReviewMetric: Identifiable {
    let id = UUID()
    let title: String
    let value: String
    let subtitle: String
}
