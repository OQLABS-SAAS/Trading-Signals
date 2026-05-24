---
name: algorithm-csharp
description: "Skill for the Algorithm.CSharp area of Trading-Signals. 845 symbols across 516 files."
---

# Algorithm.CSharp

845 symbols | 516 files | Cohesion: 70%

## When to Use

- Working with code in `research/`
- Understanding how RegressionTestException, DualThrustAlphaModel, ConstantAlphaModel work
- Modifying algorithm.csharp-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Algorithm.CSharp/CustomModelsAlgorithm.cs` | MarketFill, CreateOrderEvent, SetOrderEventToFilled, GetTradeBar, StopMarketFill (+6) |
| `research/Lean/Algorithm.CSharp/OrderTicketDemoAlgorithm.cs` | OnData, MarketOrders, LimitOrders, StopMarketOrders, StopLimitOrders (+5) |
| `research/Lean/Common/Securities/Option/OptionStrategies.cs` | Straddle, ShortStraddle, PutCalendarSpread, ShortPutCalendarSpread, CallButterfly (+4) |
| `research/Lean/Common/Orders/OrderTicket.cs` | Update, UpdateTag, UpdateQuantity, UpdateLimitPrice, UpdateStopPrice (+3) |
| `research/Lean/Algorithm.CSharp/OptionModelsConsistencyRegressionAlgorithm.cs` | Initialize, SetModels, CustomFillModel, CustomFeeModel, CustomBuyingPowerModel (+3) |
| `research/Lean/Algorithm.CSharp/SecuritySessionRegressionAlgorithm.cs` | ValidateSessionBars, Initialize, ConfigureSchedule, IsWithinMarketHours, OnData (+2) |
| `research/Lean/Tests/Common/SymbolCacheTests.cs` | HandlesRoundTripAccessSymbolToTicker, GetSymbol_ReturnsSymbolMappedByTicker_WhenExactlyOneMatch, GetSymbol_ThrowsInvalidOperation_WhenTooManyCustomDataSymbolMatches, TryGetSymbol, TryGetSymbol_FromTicker_WithConflictingSymbolWithCustomDataSuffix (+2) |
| `research/Lean/Algorithm.CSharp/PortfolioTargetTagsRegressionAlgorithm.cs` | Initialize, CustomPortfolioConstructionModel, CustomRiskManagementModel, CustomExecutionModel, CreateTargets (+2) |
| `research/Lean/Algorithm.CSharp/InsightTagAlphaRegressionAlgorithm.cs` | Initialize, OneTimeAlphaModel, OnEndOfAlgorithm, OnInsightsGeneratedVerifier, Update (+1) |
| `research/Lean/Common/Chart.cs` | Chart, AddSeries, GetUpdates, Clone, CloneEmpty (+1) |

## Entry Points

Start here when exploring this area:

- **`RegressionTestException`** (Class) — `research/Lean/Common/RegressionTestException.cs:26`
- **`DualThrustAlphaModel`** (Class) — `research/Lean/Algorithm.CSharp/Alphas/VixDualThrustAlpha.cs:85`
- **`ConstantAlphaModel`** (Class) — `research/Lean/Algorithm.Framework/Alphas/ConstantAlphaModel.cs:27`
- **`EmaCrossAlphaModel`** (Class) — `research/Lean/Algorithm.Framework/Alphas/EmaCrossAlphaModel.cs:27`
- **`HistoricalReturnsAlphaModel`** (Class) — `research/Lean/Algorithm.Framework/Alphas/HistoricalReturnsAlphaModel.cs:28`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `RegressionTestException` | Class | `research/Lean/Common/RegressionTestException.cs` | 26 |
| `DualThrustAlphaModel` | Class | `research/Lean/Algorithm.CSharp/Alphas/VixDualThrustAlpha.cs` | 85 |
| `ConstantAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/ConstantAlphaModel.cs` | 27 |
| `EmaCrossAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/EmaCrossAlphaModel.cs` | 27 |
| `HistoricalReturnsAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/HistoricalReturnsAlphaModel.cs` | 28 |
| `PearsonCorrelationPairsTradingAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/PearsonCorrelationPairsTradingAlphaModel.cs` | 29 |
| `RsiAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/RsiAlphaModel.cs` | 28 |
| `SpreadExecutionModel` | Class | `research/Lean/Algorithm.Framework/Execution/SpreadExecutionModel.cs` | 27 |
| `StandardDeviationExecutionModel` | Class | `research/Lean/Algorithm.Framework/Execution/StandardDeviationExecutionModel.cs` | 31 |
| `BlackLittermanOptimizationPortfolioConstructionModel` | Class | `research/Lean/Algorithm.Framework/Portfolio/BlackLittermanOptimizationPortfolioConstructionModel.cs` | 37 |
| `EqualWeightingPortfolioConstructionModel` | Class | `research/Lean/Algorithm.Framework/Portfolio/EqualWeightingPortfolioConstructionModel.cs` | 30 |
| `MaximumDrawdownPercentPerSecurity` | Class | `research/Lean/Algorithm.Framework/Risk/MaximumDrawdownPercentPerSecurity.cs` | 26 |
| `MaximumDrawdownPercentPortfolio` | Class | `research/Lean/Algorithm.Framework/Risk/MaximumDrawdownPercentPortfolio.cs` | 26 |
| `MaximumSectorExposureRiskManagementModel` | Class | `research/Lean/Algorithm.Framework/Risk/MaximumSectorExposureRiskManagementModel.cs` | 28 |
| `MaximumUnrealizedProfitPercentPerSecurity` | Class | `research/Lean/Algorithm.Framework/Risk/MaximumUnrealizedProfitPercentPerSecurity.cs` | 26 |
| `TrailingStopRiskManagementModel` | Class | `research/Lean/Algorithm.Framework/Risk/TrailingStopRiskManagementModel.cs` | 26 |
| `CoarseFundamentalUniverseSelectionModel` | Class | `research/Lean/Algorithm.Framework/Selection/CoarseFundamentalUniverseSelectionModel.cs` | 25 |
| `EmaCrossUniverseSelectionModel` | Class | `research/Lean/Algorithm.Framework/Selection/EmaCrossUniverseSelectionModel.cs` | 29 |
| `FineFundamentalUniverseSelectionModel` | Class | `research/Lean/Algorithm.Framework/Selection/FineFundamentalUniverseSelectionModel.cs` | 26 |
| `InceptionDateUniverseSelectionModel` | Class | `research/Lean/Algorithm.Framework/Selection/InceptionDateUniverseSelectionModel.cs` | 26 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Securities | 76 calls |
| Option | 32 calls |
| Algorithm | 23 calls |
| Util | 21 calls |
| Fills | 21 calls |
| Portfolio | 17 calls |
| Scheduling | 13 calls |
| Data | 13 calls |

## How to Explore

1. `gitnexus_context({name: "RegressionTestException"})` — see callers and callees
2. `gitnexus_query({query: "algorithm.csharp"})` — find related execution flows
3. Read key files listed above for implementation details
