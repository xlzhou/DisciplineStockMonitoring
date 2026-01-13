# Rule Expression Language (expression-v1)

## Overview
Expressions are used in condition_expr fields and support indicators, offsets, arithmetic, and logical operators.

## Identifiers
- Price series: Close, Open, High, Low, Volume
- Indicator functions: SMA(n), EMA(n), RSI(n), VWAP(n)
- Risk fields: risk.account.<field>, risk.strategy.<field>, risk.ticker.<field>

## Offsets
Square brackets access historical bars.
- Close[1] is the previous close
- High[3] is the high 3 bars ago
- SMA(20)[0] is the current SMA(20)

## Operators
- Comparison: gt, gte, lt, lte, eq, ne
- Cross: crossover, crossunder
- Logical: AND, OR, NOT
- Arithmetic: +, -, *, /
- Functions: highest(series, n), lowest(series, n), change(x), diff(x, y)

## Examples
- Close[1]
- High[3]
- SMA(20)[0]
- Close - Close[1]
- (Close[0] / Close[5] - 1) * 100
- Close > Close[10]
- RSI(14)[0] gt RSI(14)[1]
- SMA(5)[0] gt SMA(20)[0] AND SMA(5)[1] lte SMA(20)[1]
- (Close / Close[20] - 1) * 100
- Volume[0] gt Volume[1] * 1.5
- (Volume / Volume[1] - 1) * 100 > 50

## Operator semantics
- crossover(a, b): true when a[t] > b[t] and a[t-1] <= b[t-1]
- crossunder(a, b): true when a[t] < b[t] and a[t-1] >= b[t-1]
- highest(series, n): max value over last n bars (inclusive of current)
- lowest(series, n): min value over last n bars (inclusive of current)
- change(x): x[t] - x[t-1]
- diff(x, y): x - y

## Notes
- Expression tokens are case-sensitive; use the exact identifiers above.
- Offsets must be non-negative integers.
- Division by zero yields an ERROR status and BLOCK.
