//
//  ContentView.swift
//  DisciplineStockMonitoring
//
//  Created by 周晓凌 on 2026/1/14.
//

import SwiftUI
struct ContentView: View {
    var body: some View {
        TabView {
            StatusView()
                .tabItem {
                    Label("Status", systemImage: "shield.checkered")
                }
            PortfolioView()
                .tabItem {
                    Label("Portfolio", systemImage: "tray.full")
                }
            ActionsView()
                .tabItem {
                    Label("Actions", systemImage: "checkmark.seal")
                }
            ReviewView()
                .tabItem {
                    Label("Review", systemImage: "chart.bar.xaxis")
                }
        }
    }
}

#Preview {
    ContentView()
}
