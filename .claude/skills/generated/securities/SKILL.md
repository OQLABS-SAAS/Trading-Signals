---
name: securities
description: "Skill for the Securities area of Trading-Signals. 1324 symbols across 431 files."
---

# Securities

1324 symbols | 431 files | Cohesion: 50%

## When to Use

- Working with code in `research/`
- Understanding how Collective2PortfolioSignalExportDemonstrationAlgorithm, Collective2SignalExportDemonstrationAlgorithm, FutureOptionMultipleContractsInDifferentContractMonthsWithSameUnderlyingFutureRegressionAlgorithm work
- Modifying securities-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Tests/Common/Securities/SecurityPortfolioManagerTests.cs` | TestCashFills, FullExerciseCallAddsUnderlyingPositionReducesCash, ExerciseOTMCallDoesntChangeAnything, CashSettledExerciseOTMPutDoesntChangeAnything, FullExercisePutAddsUnderlyingPositionAddsCash (+44) |
| `research/Lean/Tests/Common/Securities/SecurityExchangeHoursTests.cs` | IntervalOverlappingStartIsOpen, IntervalOverlappingEndIsOpen, MultiDayInterval, MarketIsNotOpenForIntervalAfterEarlyClose, MarketIsNotOpenForIntervalBeforeLateOpen (+44) |
| `research/Lean/Tests/Common/Securities/SecurityMarginModelTests.cs` | FreeBuyingPowerPercentDefault_Option, MarginRemainingForLeverage, ZeroTargetWithZeroHoldingsIsNotAnError, ReturnsMinimumOrderValueReason, ReducesPositionWhenMarginAboveTargetWhenNegativeFreeMargin (+39) |
| `research/Lean/Tests/Common/Securities/CashBuyingPowerModelTests.cs` | Initialize, LimitBuyBtcWithUsdRequiresUsdInPortfolio, LimitBuyBtcWithEurRequiresEurInPortfolio, LimitSellOrderRequiresBaseCurrencyInPortfolio, LimitBuyOrderChecksOpenOrders (+30) |
| `research/Lean/Tests/Common/Securities/OptionPriceModelTests.cs` | CreateOption, PutCallParityTest, ExpirationDate, ChangesWithEvaluationDate, BlackScholesPortfolioTest (+26) |
| `research/Lean/Tests/Common/Securities/SecurityPortfolioModelTests.cs` | NonAccountCurrencyEquity_LongToFlat, NonAccountCurrencyEquity_ShortToFlat, NonAccountCurrencyEquity_FlatToShort, NonAccountCurrencyEquity_FlatToLong, NonAccountCurrencyFuture_LongToFlat (+16) |
| `research/Lean/Tests/Common/Securities/MarketHoursDatabaseTests.cs` | RetrievesExchangeHoursWithAndWithoutSymbol, CorrectlyReadsClosedAllDayHours, CorrectlyReadsOpenAllDayHours, CorrectlyReadsUsEquityMarketHours, CorrectlyReadsUsEquityEarlyCloses (+15) |
| `research/Lean/Common/Securities/SecurityTransactionManager.cs` | AddOrder, SecurityTransactionManager, SetOrderProcessor, AddTransactionRecord, CancelOpenOrders (+13) |
| `research/Lean/Tests/Common/Securities/DynamicSecurityDataTests.cs` | SetUp, Get_UsesTypeName_AsKey_And_ReturnsLastItem, AccessesDataDynamically, DataCanNotBeSetDynamically, AccessingPropertyThatDoesNotExists_ThrowsKeyNotFoundException_WhenNotIncludedInRegisteredTypes (+13) |
| `research/Lean/Tests/Common/Securities/FutureMarginBuyingPowerModelTests.cs` | TestMarginForSymbolWithOneLinerHistory, TestMarginForSymbolWithNoHistory, TestMarginForSymbolWithHistory, MarginUsedForPositionWhenPriceDrops, MarginUsedForPositionWhenPriceIncreases (+13) |

## Entry Points

Start here when exploring this area:

- **`Collective2PortfolioSignalExportDemonstrationAlgorithm`** (Class) — `research/Lean/Algorithm.CSharp/Collective2PortfolioSignalExportDemonstrationAlgorithm.cs:31`
- **`Collective2SignalExportDemonstrationAlgorithm`** (Class) — `research/Lean/Algorithm.CSharp/Collective2SignalExportDemonstrationAlgorithm.cs:31`
- **`FutureOptionMultipleContractsInDifferentContractMonthsWithSameUnderlyingFutureRegressionAlgorithm`** (Class) — `research/Lean/Algorithm.CSharp/FutureOptionMultipleContractsInDifferentContractMonthsWithSameUnderlyingFutureRegressionAlgorithm.cs:27`
- **`BasePairsTradingAlphaModel`** (Class) — `research/Lean/Algorithm.Framework/Alphas/BasePairsTradingAlphaModel.cs:32`
- **`RiskManagementModelPythonWrapper`** (Class) — `research/Lean/Algorithm/Risk/RiskManagementModelPythonWrapper.cs:26`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Collective2PortfolioSignalExportDemonstrationAlgorithm` | Class | `research/Lean/Algorithm.CSharp/Collective2PortfolioSignalExportDemonstrationAlgorithm.cs` | 31 |
| `Collective2SignalExportDemonstrationAlgorithm` | Class | `research/Lean/Algorithm.CSharp/Collective2SignalExportDemonstrationAlgorithm.cs` | 31 |
| `FutureOptionMultipleContractsInDifferentContractMonthsWithSameUnderlyingFutureRegressionAlgorithm` | Class | `research/Lean/Algorithm.CSharp/FutureOptionMultipleContractsInDifferentContractMonthsWithSameUnderlyingFutureRegressionAlgorithm.cs` | 27 |
| `BasePairsTradingAlphaModel` | Class | `research/Lean/Algorithm.Framework/Alphas/BasePairsTradingAlphaModel.cs` | 32 |
| `RiskManagementModelPythonWrapper` | Class | `research/Lean/Algorithm/Risk/RiskManagementModelPythonWrapper.cs` | 26 |
| `CustomUniverse` | Class | `research/Lean/Algorithm/Selection/CustomUniverse.cs` | 28 |
| `FxcmBrokerageModel` | Class | `research/Lean/Common/Brokerages/FxcmBrokerageModel.cs` | 29 |
| `FundamentalUniverse` | Class | `research/Lean/Common/Data/Fundamental/FundamentalUniverse.cs` | 31 |
| `Tick` | Class | `research/Lean/Common/Data/Market/Tick.cs` | 31 |
| `SubscriptionDataConfig` | Class | `research/Lean/Common/Data/SubscriptionDataConfig.cs` | 28 |
| `NewSymbolEventArgs` | Class | `research/Lean/Common/Data/SubscriptionDataConfig.cs` | 416 |
| `SubscriptionManager` | Class | `research/Lean/Common/Data/SubscriptionManager.cs` | 31 |
| `CoarseFundamentalUniverse` | Class | `research/Lean/Common/Data/UniverseSelection/CoarseFundamentalUniverse.cs` | 25 |
| `SubscriptionRequest` | Class | `research/Lean/Common/Data/UniverseSelection/SubscriptionRequest.cs` | 24 |
| `LocalTimeKeeper` | Class | `research/Lean/Common/LocalTimeKeeper.cs` | 24 |
| `BinanceOrderProperties` | Class | `research/Lean/Common/Orders/BinanceOrderProperties.cs` | 22 |
| `BybitOrderProperties` | Class | `research/Lean/Common/Orders/BybitOrderProperties.cs` | 20 |
| `AlphaStreamsFeeModel` | Class | `research/Lean/Common/Orders/Fees/AlphaStreamsFeeModel.cs` | 24 |
| `Fill` | Class | `research/Lean/Common/Orders/Fills/Fill.cs` | 23 |
| `KrakenOrderProperties` | Class | `research/Lean/Common/Orders/KrakenOrderProperties.cs` | 21 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Fills | 331 calls |
| Algorithm | 270 calls |
| Algorithm.CSharp | 156 calls |
| DataFeeds | 111 calls |
| Fees | 88 calls |
| BrokerageTransactionHandlerTests | 75 calls |
| Util | 62 calls |
| Positions | 43 calls |

## How to Explore

1. `gitnexus_context({name: "Collective2PortfolioSignalExportDemonstrationAlgorithm"})` — see callers and callees
2. `gitnexus_query({query: "securities"})` — find related execution flows
3. Read key files listed above for implementation details
