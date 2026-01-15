import Foundation

typealias JSONMap = [String: Any]

struct RulePlanDTO {
    let id: Int
    let stockId: Int
    let version: Int
    let isActive: Bool
    let rules: JSONMap
    let notes: String?
    let createdAt: String

    init?(dict: JSONMap) {
        guard
            let id = Self.intValue(dict["id"]),
            let stockId = Self.intValue(dict["stock_id"]),
            let version = Self.intValue(dict["version"]),
            let isActive = Self.boolValue(dict["is_active"]),
            let rules = dict["rules"] as? JSONMap,
            let createdAt = dict["created_at"] as? String
        else {
            return nil
        }
        self.id = id
        self.stockId = stockId
        self.version = version
        self.isActive = isActive
        self.rules = rules
        self.notes = dict["notes"] as? String
        self.createdAt = createdAt
    }

    private static func intValue(_ value: Any?) -> Int? {
        if let value = value as? Int {
            return value
        }
        if let value = value as? NSNumber {
            return value.intValue
        }
        if let value = value as? Double {
            return Int(value)
        }
        return nil
    }

    private static func boolValue(_ value: Any?) -> Bool? {
        if let value = value as? Bool {
            return value
        }
        if let value = value as? NSNumber {
            return value.boolValue
        }
        return nil
    }
}
