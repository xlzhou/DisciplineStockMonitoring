import Foundation

struct StockDTO: Identifiable, Decodable {
    let id: Int
    let ticker: String
    let market: String
    let currency: String
    let status: String
    let positionState: String
    let avgEntryPrice: Double?
    let positionQty: Int?
    let createdAt: String
}

struct StockPriceDTO: Identifiable, Decodable {
    let id: Int
    let ticker: String
    let market: String
    let currency: String
    let status: String
    let positionState: String
    let createdAt: String
    let price: Double?
}

struct StockPriceOnlyDTO: Identifiable, Decodable {
    let id: Int
    let ticker: String
    let price: Double?
}

struct StockCreateRequest: Encodable {
    let ticker: String
    let market: String
    let currency: String
    let status: String
    let positionState: String
    let avgEntryPrice: Double?
    let positionQty: Int?
}

struct TickerValidationDTO: Decodable {
    let ticker: String
    let valid: Bool
    let status: String?
}
