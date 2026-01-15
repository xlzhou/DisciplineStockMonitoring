import SwiftUI

struct ReviewView: View {
    @StateObject private var viewModel = ReviewViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if viewModel.isLoading {
                        ProgressView()
                    } else if let errorMessage = viewModel.errorMessage {
                        Text(errorMessage)
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    } else {
                        Text("Discipline Metrics")
                            .font(.headline)

                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            ForEach(viewModel.metrics) { metric in
                                MetricCard(metric: metric)
                            }
                        }

                        Text("Audit Log")
                            .font(.headline)
                            .padding(.top, 8)

                        VStack(spacing: 10) {
                            ForEach(viewModel.events) { event in
                                AuditRow(event: event)
                            }
                        }
                    }
                }
                .padding()
            }
            .refreshable {
                await viewModel.load()
            }
            .navigationTitle("Review")
            .task {
                await viewModel.load()
            }
        }
    }
}

private struct MetricCard: View {
    let metric: ReviewMetric

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(metric.title)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text(metric.value)
                .font(.title2.weight(.semibold))
            Text(metric.subtitle)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

private struct AuditRow: View {
    let event: AuditEvent

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(event.eventType)
                    .font(.subheadline.weight(.semibold))
                Text(event.detail)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            Spacer()
            Text(event.timestamp)
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding(12)
        .background(Color(.systemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

#Preview {
    ReviewView()
}
