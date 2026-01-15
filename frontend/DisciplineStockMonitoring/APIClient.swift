import Foundation

enum APIError: Error {
    case invalidResponse
    case httpStatus(Int)
    case httpStatusWithBody(Int, String)
}

final class APIClient {
    static let shared = APIClient(baseURL: AppConfig.apiBaseURL)

    private let baseURL: URL
    private let session: URLSession

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func fetchStocks() async throws -> [StockDTO] {
        try await request(path: "/stocks")
    }

    func fetchStocksWithPrices() async throws -> [StockPriceDTO] {
        try await request(path: "/stocks/with-prices")
    }

    func fetchStockPrices() async throws -> [StockPriceOnlyDTO] {
        try await request(path: "/stocks/prices")
    }

    func fetchRulePlans(stockId: Int) async throws -> [RulePlanDTO] {
        let raw = try await requestRaw(path: "/stocks/\(stockId)/rule-plans")
        guard let array = raw as? [JSONMap] else {
            throw APIError.invalidResponse
        }
        return array.compactMap { RulePlanDTO(dict: $0) }
    }

    func createRulePlan(stockId: Int, rules: JSONMap) async throws -> RulePlanDTO {
        let url = baseURL.appendingPathComponent("/stocks/\(stockId)/rule-plans/raw")
        let data = try JSONSerialization.data(withJSONObject: rules, options: [])
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = data
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (responseData, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.httpStatusWithBody(http.statusCode, body)
        }
        let raw = try JSONSerialization.jsonObject(with: responseData)
        guard let dict = raw as? JSONMap, let plan = RulePlanDTO(dict: dict) else {
            throw APIError.invalidResponse
        }
        return plan
    }

    func createStock(_ payload: StockCreateRequest) async throws -> StockDTO {
        let url = baseURL.appendingPathComponent("/stocks")
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = try JSONEncoder.api.encode(payload)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.httpStatusWithBody(http.statusCode, body)
        }
        return try JSONDecoder.api.decode(StockDTO.self, from: data)
    }

    func updateStock(id: Int, payload: [String: Any]) async throws -> StockDTO {
        let url = baseURL.appendingPathComponent("/stocks/\(id)")
        let data = try JSONSerialization.data(withJSONObject: payload, options: [])
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.httpBody = data
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (responseData, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: responseData, encoding: .utf8) ?? ""
            throw APIError.httpStatusWithBody(http.statusCode, body)
        }
        return try JSONDecoder.api.decode(StockDTO.self, from: responseData)
    }

    func archiveStock(id: Int) async throws -> StockDTO {
        let url = baseURL.appendingPathComponent("/stocks/\(id)")
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw APIError.httpStatusWithBody(http.statusCode, body)
        }
        return try JSONDecoder.api.decode(StockDTO.self, from: data)
    }

    func validateTicker(_ ticker: String, market: String) async throws -> TickerValidationDTO {
        let path = "/stocks/validate/\(ticker)?market=\(market)"
        return try await request(path: path)
    }

    private func request<T: Decodable>(path: String) async throws -> T {
        let url = baseURL.appendingPathComponent(path)
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.httpStatus(http.statusCode)
        }
        return try JSONDecoder.api.decode(T.self, from: data)
    }

    private func requestRaw(path: String) async throws -> Any {
        let url = baseURL.appendingPathComponent(path)
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.httpStatus(http.statusCode)
        }
        return try JSONSerialization.jsonObject(with: data)
    }
}

extension JSONDecoder {
    static let api: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()
}

extension JSONEncoder {
    static let api: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()
}
