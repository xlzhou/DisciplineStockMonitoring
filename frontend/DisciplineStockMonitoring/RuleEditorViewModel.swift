import Foundation
import Combine

@MainActor
final class RuleEditorViewModel: ObservableObject {
    @Published private(set) var isLoading = false
    @Published private(set) var errorMessage: String?
    @Published var jsonText: String = ""

    private let apiClient: APIClient
    private var latestVersion = 0

    init(apiClient: APIClient? = nil) {
        self.apiClient = apiClient ?? APIClient(baseURL: AppConfig.apiBaseURL)
    }

    func load(stockId: Int) async {
        isLoading = true
        errorMessage = nil
        do {
            let plans = try await apiClient.fetchRulePlans(stockId: stockId)
            if let active = plans.first(where: { $0.isActive }) ?? plans.sorted(by: { $0.version > $1.version }).first {
                latestVersion = active.version
                jsonText = prettyJSON(active.rules)
            } else {
                latestVersion = 0
            }
        } catch {
            errorMessage = "Failed to load rule plan"
        }
        isLoading = false
    }

    func save(stockId: Int, rules: JSONMap) async -> String? {
        isLoading = true
        errorMessage = nil
        do {
            let _ = try await apiClient.createRulePlan(
                stockId: stockId,
                rules: rules
            )
            latestVersion += 1
            jsonText = prettyJSON(rules)
            isLoading = false
            return nil
        } catch {
            errorMessage = "Failed to save rule plan: \(error.localizedDescription)"
            isLoading = false
            return errorMessage
        }
    }

    func parseJSONText() -> JSONMap? {
        guard let data = jsonText.data(using: .utf8) else {
            return nil
        }
        let json = try? JSONSerialization.jsonObject(with: data)
        return json as? JSONMap
    }

    private func prettyJSON(_ dict: JSONMap) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted, .sortedKeys]) else {
            return "{}"
        }
        return String(data: data, encoding: .utf8) ?? "{}"
    }
}
