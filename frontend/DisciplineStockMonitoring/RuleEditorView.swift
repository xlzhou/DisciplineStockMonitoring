import SwiftUI

struct RuleEditorView: View {
    let stockId: Int
    let ticker: String
    @StateObject private var viewModel = RuleEditorViewModel()
    @State private var showingJSON = false
    @State private var strategyType = "Swing"
    @State private var maxHoldingDays = "60"
    @State private var cooldownDays = "10"
    @State private var targetPct = "0.10"
    @State private var maxPct = "0.15"
    @State private var entryRule = "Close crossover SMA(20)"
    @State private var stopLoss = "8%"
    @State private var takeProfit = "8% / 15%"
    @State private var takeProfitSize = "50% / 50%"
    @State private var trailingStop = "6%"
    @State private var earningsBlockDays = "3"
    @State private var confirmationDelay = "60"
    @State private var requireReason = true
    @State private var saveMessage: String?
    @State private var isSyncing = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header

                Toggle("Raw JSON View", isOn: $showingJSON)
                    .onChange(of: showingJSON) {
                        guard !isSyncing else { return }
                        if showingJSON {
                            viewModel.jsonText = prettyJSON(buildRulesFromForm())
                        } else {
                            if let rules = viewModel.parseJSONText() {
                                applyRulesToForm(rules)
                            }
                        }
                    }

                if viewModel.isLoading {
                    ProgressView()
                } else {
                    if showingJSON {
                        VStack(alignment: .leading, spacing: 8) {
                            jsonEditor
                            Button("Copy JSON") {
                                UIPasteboard.general.string = viewModel.jsonText
                            }
                            .buttonStyle(.bordered)
                        }
                    } else {
                        formSections
                    }
                }

                if let saveMessage {
                    Text(saveMessage)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }

                Button("Save Rule Plan") {
                    Task {
                        await saveRules()
                    }
                }
                .buttonStyle(.borderedProminent)
            }
            .padding()
        }
        .navigationTitle("Rule Editor")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            await viewModel.load(stockId: stockId)
            if let rules = viewModel.parseJSONText() {
                applyRulesToForm(rules)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Write a contract with yourself")
                .font(.headline)
            Text("Missing rules will block actions.")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    private var formSections: some View {
        VStack(alignment: .leading, spacing: 16) {
            formSection(title: "Position Intent") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Strategy type")
                        .font(.subheadline)
                    Picker("Strategy type", selection: $strategyType) {
                        Text("Swing").tag("Swing")
                        Text("Long-Term").tag("Long-Term")
                        Text("Position").tag("Position")
                    }
                    .pickerStyle(.menu)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Max holding days")
                        .font(.subheadline)
                    TextField("e.g. 60", text: $maxHoldingDays)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Cooldown after exit (days)")
                        .font(.subheadline)
                    TextField("e.g. 10", text: $cooldownDays)
                }
            }

            formSection(title: "Position Sizing") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Target %")
                        .font(.subheadline)
                    TextField("e.g. 10% or 0.10", text: $targetPct)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Max %")
                        .font(.subheadline)
                    TextField("e.g. 15% or 0.15", text: $maxPct)
                }
            }

            formSection(title: "Entry Rules") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Primary entry rule")
                        .font(.subheadline)
                    TextField("e.g. Close crossover SMA(20)", text: $entryRule)
                }
            }

            formSection(title: "Exit Rules") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Hard stop-loss")
                        .font(.subheadline)
                    TextField("e.g. 8% or 0.08", text: $stopLoss)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Take profit")
                        .font(.subheadline)
                    TextField("e.g. 8% / 15% or 0.08 / 0.15", text: $takeProfit)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Take profit size")
                        .font(.subheadline)
                    TextField("e.g. 20% / 80% or 0.2 / 0.8", text: $takeProfitSize)
                }
                VStack(alignment: .leading, spacing: 6) {
                    Text("Trailing stop")
                        .font(.subheadline)
                    TextField("e.g. 6% or 0.06", text: $trailingStop)
                }
            }

            formSection(title: "Risk Blocks") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Earnings block days")
                        .font(.subheadline)
                    TextField("e.g. 3", text: $earningsBlockDays)
                }
            }

            formSection(title: "Behavior Controls") {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Confirmation delay (sec)")
                        .font(.subheadline)
                    TextField("e.g. 60", text: $confirmationDelay)
                }
                Toggle("Require override reason", isOn: $requireReason)
            }
        }
    }

    private var jsonEditor: some View {
        TextEditor(text: $viewModel.jsonText)
            .font(.system(.footnote, design: .monospaced))
            .frame(minHeight: 240)
            .padding(8)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private func formSection<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            content()
                .textFieldStyle(.roundedBorder)
        }
        .padding(16)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private func saveRules() async {
        saveMessage = nil
        let rules: JSONMap
        if showingJSON, let parsed = viewModel.parseJSONText() {
            rules = parsed
        } else {
            rules = buildRulesFromForm()
        }

        let error = await viewModel.save(stockId: stockId, rules: rules)
        if let error {
            saveMessage = error
        } else {
            saveMessage = "Saved"
        }
    }

    private func applyRulesToForm(_ rules: JSONMap) {
        isSyncing = true
        defer { isSyncing = false }

        if let strategy = rules["strategy_type"] as? String {
            strategyType = strategy.capitalized.replacingOccurrences(of: "-", with: "-")
        }
        if let intent = rules["position_intent"] as? JSONMap {
            if let maxHolding = intent["max_holding_days"] as? Int {
                maxHoldingDays = String(maxHolding)
            }
            if let cooldown = intent["cooldown_days_after_exit"] as? Int {
                cooldownDays = String(cooldown)
            }
        }
        if let sizing = rules["position_sizing"] as? JSONMap {
            if let target = sizing["target_pct"] as? Double {
                targetPct = formatPercent(target)
            }
            if let max = sizing["max_pct"] as? Double {
                maxPct = formatPercent(max)
            }
        }
        if let entries = rules["entry_rules"] as? [JSONMap],
           let first = entries.first,
           let expr = first["condition_expr"] as? String {
            entryRule = expr
        }
        if let exit = rules["exit_rules"] as? JSONMap {
            if let hard = exit["hard_stop"] as? JSONMap,
               let value = hard["value"] as? Double {
                stopLoss = formatPercent(value)
            }
            if let trailing = exit["trailing_stop"] as? JSONMap,
               let value = trailing["value"] as? Double {
                trailingStop = formatPercent(value)
            }
            if let profits = exit["take_profits"] as? [JSONMap] {
                let pctList = profits.compactMap { item -> String? in
                    guard let pct = item["pct_gain"] as? Double else { return nil }
                    return formatPercent(pct)
                }
                let sizeList = profits.compactMap { item -> String? in
                    guard let size = item["size_pct"] as? Double else { return nil }
                    return formatPercent(size)
                }
                if !pctList.isEmpty {
                    takeProfit = pctList.joined(separator: " / ")
                }
                if !sizeList.isEmpty {
                    takeProfitSize = sizeList.joined(separator: " / ")
                }
            }
        }
        if let risk = rules["risk_rules"] as? JSONMap,
           let ticker = risk["ticker"] as? JSONMap,
           let days = ticker["earnings_window_block_days"] as? Int {
            earningsBlockDays = String(days)
        }
        if let behavior = rules["behavior_controls"] as? JSONMap {
            if let delay = behavior["confirmation_delay_sec"] as? Int {
                confirmationDelay = String(delay)
            }
            if let require = behavior["require_override_reason"] as? Bool {
                requireReason = require
            }
        }
    }

    private func buildRulesFromForm() -> JSONMap {
        let maxHolding = Int(maxHoldingDays) ?? 60
        let cooldown = Int(cooldownDays) ?? 10
        let target = Double(targetPct) ?? 0.1
        let max = Double(maxPct) ?? 0.15
        let confirmation = Int(confirmationDelay) ?? 60
        let earningsBlock = Int(earningsBlockDays) ?? 3

        let stopLossPct = parsePercent(stopLoss, fallback: 0.08)
        let trailingPct = parsePercent(trailingStop, fallback: 0.06)
        let takeProfits = parseTakeProfits(takeProfit, sizesRaw: takeProfitSize)

        return [
            "schema_version": "1.3",
            "ticker": ticker,
            "strategy_type": strategyType.lowercased(),
            "indicator_policy": [
                "timeframe": "1D",
                "price_field": "close",
                "use_eod_only": true
            ],
            "indicators": [
                ["id": "ma20", "type": "MA", "ma_type": "SMA", "period": 20],
                ["id": "ma120", "type": "MA", "ma_type": "SMA", "period": 120],
                ["id": "rsi14", "type": "RSI", "period": 14]
            ],
            "position_intent": [
                "max_holding_days": maxHolding,
                "cooldown_days_after_exit": cooldown
            ],
            "position_sizing": [
                "target_pct": target,
                "max_pct": max,
                "account_size": NSNull()
            ],
            "entry_rules": [
                [
                    "id": "E1",
                    "priority": 1,
                    "size_pct": target,
                    "condition_expr": entryRule
                ]
            ],
            "exit_rules": [
                "hard_stop": [
                    "type": "pct_below_entry",
                    "value": stopLossPct
                ],
                "take_profits": takeProfits,
                "trailing_stop": [
                    "type": "pct_from_peak",
                    "value": trailingPct
                ],
                "time_stop": [
                    "max_holding_days": maxHolding
                ]
            ],
            "risk_rules": [
                "account": [
                    "max_drawdown": 0.2,
                    "daily_loss_limit": 0.05,
                    "max_position_value": 0.8
                ],
                "strategy": [
                    "max_allocation": 0.3,
                    "max_concurrent_trades": 5,
                    "strategy_max_drawdown": 0.15
                ],
                "ticker": [
                    "max_position_pct": max,
                    "max_loss_per_ticker": 0.03,
                    "blacklist": [],
                    "earnings_window_block_days": earningsBlock
                ]
            ],
            "behavior_controls": [
                "confirmation_delay_sec": confirmation,
                "require_override_reason": requireReason,
                "daily_action_limit": 2
            ]
        ]
    }

    private func parsePercent(_ raw: String, fallback: Double) -> Double {
        let trimmed = raw.replacingOccurrences(of: "%", with: "")
        if let value = Double(trimmed) {
            return value > 1 ? value / 100.0 : value
        }
        return fallback
    }

    private func formatPercent(_ value: Double) -> String {
        let percent = value * 100
        if percent.rounded() == percent {
            return String(format: "%.0f%%", percent)
        }
        return String(format: "%.2f%%", percent)
    }

    private func prettyJSON(_ dict: JSONMap) -> String {
        guard let data = try? JSONSerialization.data(withJSONObject: dict, options: [.prettyPrinted, .sortedKeys]) else {
            return "{}"
        }
        return String(data: data, encoding: .utf8) ?? "{}"
    }

    private func parseTakeProfits(_ raw: String, sizesRaw: String) -> [[String: Any]] {
        let parts = raw.split(separator: "/").map { $0.trimmingCharacters(in: .whitespaces) }
        let sizeParts = sizesRaw.split(separator: "/").map { $0.trimmingCharacters(in: .whitespaces) }
        var results: [[String: Any]] = []
        for (index, part) in parts.enumerated() {
            let pct = parsePercent(part, fallback: 0.08 + Double(index) * 0.07)
            let sizeFallback = 1.0 / Double(max(parts.count, 1))
            let sizeRaw = index < sizeParts.count ? sizeParts[index] : ""
            let sizePct = sizeRaw.isEmpty ? sizeFallback : parsePercent(sizeRaw, fallback: sizeFallback)
            results.append([
                "id": "TP\(index + 1)",
                "pct_gain": pct,
                "size_pct": sizePct
            ])
        }
        if results.isEmpty {
            results = [[
                "id": "TP1",
                "pct_gain": 0.08,
                "size_pct": 1.0
            ]]
        }
        return results
    }
}

#Preview {
    NavigationStack {
        RuleEditorView(stockId: 1, ticker: "AAPL")
    }
}
