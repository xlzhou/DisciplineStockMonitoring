import SwiftUI

struct RuleEditorView: View {
    @State private var showingJSON = false
    @State private var strategyType = "Swing"
    @State private var maxHoldingDays = "60"
    @State private var cooldownDays = "10"
    @State private var targetPct = "0.10"
    @State private var maxPct = "0.15"
    @State private var entryRule = "Close crossover SMA(20)"
    @State private var stopLoss = "8%"
    @State private var takeProfit = "8% / 15%"
    @State private var trailingStop = "6%"
    @State private var earningsBlockDays = "3"
    @State private var confirmationDelay = "60"
    @State private var requireReason = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header

                Toggle("Raw JSON View", isOn: $showingJSON)

                if showingJSON {
                    jsonPreview
                } else {
                    formSections
                }

                Button("Save Rule Plan") {}
                    .buttonStyle(.borderedProminent)
            }
            .padding()
        }
        .navigationTitle("Rule Editor")
        .navigationBarTitleDisplayMode(.inline)
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
                TextField("Strategy type", text: $strategyType)
                TextField("Max holding days", text: $maxHoldingDays)
                TextField("Cooldown after exit (days)", text: $cooldownDays)
            }

            formSection(title: "Position Sizing") {
                TextField("Target %", text: $targetPct)
                TextField("Max %", text: $maxPct)
            }

            formSection(title: "Entry Rules") {
                TextField("Primary entry rule", text: $entryRule)
            }

            formSection(title: "Exit Rules") {
                TextField("Hard stop-loss", text: $stopLoss)
                TextField("Take profit", text: $takeProfit)
                TextField("Trailing stop", text: $trailingStop)
            }

            formSection(title: "Risk Blocks") {
                TextField("Earnings block days", text: $earningsBlockDays)
            }

            formSection(title: "Behavior Controls") {
                TextField("Confirmation delay (sec)", text: $confirmationDelay)
                Toggle("Require override reason", isOn: $requireReason)
            }
        }
    }

    private var jsonPreview: some View {
        Text(sampleJSON)
            .font(.system(.footnote, design: .monospaced))
            .foregroundColor(.secondary)
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }

    private var sampleJSON: String {
        """
        {
          "schema_version": "1.3",
          "strategy_type": "\(strategyType)",
          "position_intent": {
            "max_holding_days": \(maxHoldingDays),
            "cooldown_days_after_exit": \(cooldownDays)
          },
          "position_sizing": {
            "target_pct": \(targetPct),
            "max_pct": \(maxPct)
          },
          "entry_rules": [
            { "id": "E1", "condition_expr": "\(entryRule)" }
          ],
          "exit_rules": {
            "hard_stop": "\(stopLoss)",
            "take_profit": "\(takeProfit)",
            "trailing_stop": "\(trailingStop)"
          },
          "behavior_controls": {
            "confirmation_delay_sec": \(confirmationDelay),
            "require_override_reason": \(requireReason)
          }
        }
        """
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
}

#Preview {
    NavigationStack {
        RuleEditorView()
    }
}
