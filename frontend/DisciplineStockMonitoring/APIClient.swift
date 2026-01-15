import Foundation

enum APIError: Error {
    case invalidResponse
    case httpStatus(Int)
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
            throw APIError.httpStatus(http.statusCode)
        }
        return try JSONDecoder.api.decode(StockDTO.self, from: data)
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
            throw APIError.httpStatus(http.statusCode)
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
