//
//  Item.swift
//  DisciplineStockMonitoring
//
//  Created by 周晓凌 on 2026/1/14.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
