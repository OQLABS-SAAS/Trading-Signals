---
name: algorithm
description: "Skill for the Algorithm area of Trading-Signals. 956 symbols across 177 files."
---

# Algorithm

956 symbols | 177 files | Cohesion: 61%

## When to Use

- Working with code in `research/`
- Understanding how NullPortfolioConstructionModel, QCAlgorithm, DefaultBrokerageMessageHandler work
- Modifying algorithm-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Algorithm/QCAlgorithm.Indicators.cs` | ABANDS, AD, ADOSC, AR, ARIMA (+153) |
| `research/Lean/Tests/Algorithm/AlgorithmHistoryTests.cs` | Setup, TickResolutionOpenInterestHistoryRequestIsFilteredByDefault_MultipleSymbols, TickHistoryReturnsConsistentResultsWithOrWithoutEquity, HistoryRequestUsesSecurityConfigOrExplicitValues, CustomTestHistoryProvider (+81) |
| `research/Lean/Algorithm/QCAlgorithm.cs` | QCAlgorithm, PostInitialize, SetAvailableDataTypes, SetDateTime, SetCash (+68) |
| `research/Lean/Algorithm/ConstituentUniverseDefinitions.cs` | AggressiveGrowth, ClassicGrowth, Cyclicals, Distressed, HardAsset (+67) |
| `research/Lean/Tests/Algorithm/AlgorithmTradingTests.cs` | SetHoldings_Long_RoundOff, SetHoldings_Short_RoundOff, SetHoldings_Long_ToZero_RoundOff, SetHoldings_ZeroToLong, SetHoldings_ZeroToLong_SmallConstantFeeStructure (+66) |
| `research/Lean/Tests/Algorithm/CashModelAlgorithmTradingTests.cs` | SetHoldings_ZeroToLong, SetHoldings_ZeroToLong_SmallConstantFeeStructure, SetHoldings_ZeroToLong_HighConstantFeeStructure, SetHoldings_LongToLonger, SetHoldings_LongToFullLong (+27) |
| `research/Lean/Algorithm/QCAlgorithm.History.cs` | History, TryGetWarmupHistoryStartTime, History, History, History (+25) |
| `research/Lean/Algorithm/QCAlgorithm.Trading.cs` | MarketOrder, MarketOnOpenOrder, MarketOnCloseOrder, LimitOrder, StopMarketOrder (+22) |
| `research/Lean/Algorithm/QCAlgorithm.Python.cs` | History, History, History, History, History (+22) |
| `research/Lean/Tests/Algorithm/AlgorithmInitializeTests.cs` | Validates_SetBrokerageModel_AddForex, Validates_SetBrokerageModel_IB_AddForex, Validates_AddForex_SetBrokerageModel, Validates_SetBrokerageModel_AddForexWithLeverage, Validates_AddForexWithLeverage_SetBrokerageModel (+18) |

## Entry Points

Start here when exploring this area:

- **`NullPortfolioConstructionModel`** (Class) — `research/Lean/Algorithm/Portfolio/NullPortfolioConstructionModel.cs:24`
- **`QCAlgorithm`** (Class) — `research/Lean/Algorithm/QCAlgorithm.cs:69`
- **`DefaultBrokerageMessageHandler`** (Class) — `research/Lean/Common/Brokerages/DefaultBrokerageMessageHandler.cs:34`
- **`NotificationManager`** (Class) — `research/Lean/Common/Notifications/NotificationManager.cs:24`
- **`BrokerageTransactionHandler`** (Class) — `research/Lean/Engine/TransactionHandlers/BrokerageTransactionHandler.cs:42`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `NullPortfolioConstructionModel` | Class | `research/Lean/Algorithm/Portfolio/NullPortfolioConstructionModel.cs` | 24 |
| `QCAlgorithm` | Class | `research/Lean/Algorithm/QCAlgorithm.cs` | 69 |
| `DefaultBrokerageMessageHandler` | Class | `research/Lean/Common/Brokerages/DefaultBrokerageMessageHandler.cs` | 34 |
| `NotificationManager` | Class | `research/Lean/Common/Notifications/NotificationManager.cs` | 24 |
| `BrokerageTransactionHandler` | Class | `research/Lean/Engine/TransactionHandlers/BrokerageTransactionHandler.cs` | 42 |
| `NullBrokerage` | Class | `research/Lean/Tests/Algorithm/AlgorithmLiveTradingTests.cs` | 75 |
| `TestSecurityMarginModel` | Class | `research/Lean/Tests/Algorithm/AlgorithmSetHoldingsTests.cs` | 32 |
| `MockDataFeed` | Class | `research/Lean/Tests/Engine/DataFeeds/MockDataFeed.cs` | 24 |
| `PerformanceBenchmarkAlgorithms` | Class | `research/Lean/Tests/Engine/PerformanceBenchmarkAlgorithms.cs` | 24 |
| `AbsolutePriceOscillator` | Class | `research/Lean/Indicators/AbsolutePriceOscillator.cs` | 25 |
| `ChaikinOscillator` | Class | `research/Lean/Indicators/ChaikinOscillator.cs` | 20 |
| `KaufmanEfficiencyRatio` | Class | `research/Lean/Indicators/KaufmanEfficiencyRatio.cs` | 24 |
| `MomentumPercent` | Class | `research/Lean/Indicators/MomentumPercent.cs` | 23 |
| `NewHighsNewLowsVolume` | Class | `research/Lean/Indicators/NewHighsNewLowsVolume.cs` | 25 |
| `PercentagePriceOscillator` | Class | `research/Lean/Indicators/PercentagePriceOscillator.cs` | 22 |
| `RateOfChangeRatio` | Class | `research/Lean/Indicators/RateOfChangeRatio.cs` | 22 |
| `ConstituentsUniverse` | Class | `research/Lean/Common/Data/UniverseSelection/ConstituentsUniverse.cs` | 28 |
| `Symbol` | Class | `research/Lean/Common/Symbol.cs` | 30 |
| `HistoryProviderInitializeParameters` | Class | `research/Lean/Common/Data/HistoryProviderInitializeParameters.cs` | 24 |
| `DataPermissionManager` | Class | `research/Lean/Engine/DataFeeds/DataPermissionManager.cs` | 29 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Securities | 246 calls |
| Indicators | 125 calls |
| Algorithm.CSharp | 89 calls |
| Fills | 73 calls |
| DataFeeds | 47 calls |
| Fees | 45 calls |
| Data | 33 calls |
| BrokerageTransactionHandlerTests | 31 calls |

## How to Explore

1. `gitnexus_context({name: "NullPortfolioConstructionModel"})` — see callers and callees
2. `gitnexus_query({query: "algorithm"})` — find related execution flows
3. Read key files listed above for implementation details
