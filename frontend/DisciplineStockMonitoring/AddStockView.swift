import SwiftUI

struct AddStockView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var ticker = ""
    @State private var market = "US"
    @State private var currency = "USD"
    @State private var positionState = "flat"
    @State private var isSaving = false
    @State private var errorMessage: String?

    let onSave: (String, String, String, String) async -> String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Identity") {
                    TextField("Ticker", text: $ticker)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled(true)

                    Picker("Market", selection: $market) {
                        Text("US").tag("US")
                        Text("HK").tag("HK")
                        Text("CN").tag("CN")
                    }
                    .onChange(of: market) {
                        currency = defaultCurrency(for: market, current: currency)
                    }

                    TextField("Currency", text: $currency)
                        .textInputAutocapitalization(.characters)
                        .autocorrectionDisabled(true)
                }

                Section("Position State") {
                    Picker("State", selection: $positionState) {
                        Text("Flat").tag("flat")
                        Text("Holding").tag("holding")
                    }
                }

                if let errorMessage = errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("Add Stock")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        Task {
                            await save()
                        }
                    }
                    .disabled(ticker.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                }
            }
        }
    }

    private func save() async {
        isSaving = true
        errorMessage = nil
        let error = await onSave(
            ticker.trimmingCharacters(in: .whitespacesAndNewlines).uppercased(),
            market,
            currency.trimmingCharacters(in: .whitespacesAndNewlines).uppercased(),
            positionState
        )
        isSaving = false
        if error == nil {
            dismiss()
        } else {
            errorMessage = error
        }
    }

    private func defaultCurrency(for market: String, current: String) -> String {
        let mapping: [String: String] = [
            "US": "USD",
            "HK": "HKD",
            "CN": "CNY"
        ]
        return mapping[market] ?? current
    }
}

#Preview {
    AddStockView { _, _, _, _ in nil }
}
