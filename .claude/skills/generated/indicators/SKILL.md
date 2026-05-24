---
name: indicators
description: "Skill for the Indicators area of Trading-Signals. 957 symbols across 428 files."
---

# Indicators

957 symbols | 428 files | Cohesion: 65%

## When to Use

- Working with code in `research/`
- Understanding how get_candle_source, np_ffill, np_shift work
- Modifying indicators-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Indicators/IndicatorExtensions.cs` | Update, Minus, SMA, SMA, Minus (+20) |
| `research/Lean/Tests/Indicators/IndicatorExtensionsTests.cs` | PipesDataUsingOfFromFirstToSecond, MultiChainSMA, MultiChainEMA, MultiChainMAX, MultiChainMIN (+16) |
| `research/Lean/Tests/Indicators/CommonIndicatorTests.cs` | AcceptsRenkoBarsAsInput, IndicatorValueIsNotZeroAfterReceiveRenkoBars, CommonIndicatorTests, WarmsUpProperly, TimeMovesForward (+12) |
| `research/vectorbt/vectorbt/indicators/factory.py` | params_to_list, _run, _run_combs, _merge_settings, _extract_inputs (+11) |
| `research/Lean/Tests/Indicators/AlphaIndicatorTests.cs` | CreateIndicator, AcceptsRenkoBarsAsInput, AcceptsVolumeRenkoBarsAsInput, IndicatorShouldHaveSymbolAfterUpdates, TimeMovesForward (+10) |
| `research/Lean/Tests/Algorithm/AlgorithmIndicatorsTests.cs` | SpecificTTypeIndicator, CustomIndicator, BetaCalculation, IndicatorHistoryShouldIncludeValidIndicatorsAndExplicitlyIncludedProperties, TestIndicator (+7) |
| `research/Lean/Tests/Indicators/OptionBaseIndicatorTests.cs` | OptionBaseIndicatorTests, ResetsProperly, CreateIndicator, ZeroGreeksIfExpired, TimeMovesForward (+7) |
| `research/Lean/Tests/Indicators/BetaIndicatorTests.cs` | CreateIndicator, AcceptsRenkoBarsAsInput, AcceptsVolumeRenkoBarsAsInput, TimeMovesForward, WarmsUpProperly (+6) |
| `research/Lean/Tests/Indicators/TomDemarkSequentialTests.cs` | AcceptsRenkoBarsAsInput, CreateIndicator, IsReadyAfterPeriodUpdates, ResetsProperly, AcceptsVolumeRenkoBarsAsInput (+6) |
| `research/backtrader/backtrader/indicators/basicops.py` | OperationN, BaseApplyN, FindFirstIndex, FindLastIndex, PeriodN (+6) |

## Entry Points

Start here when exploring this area:

- **`get_candle_source`** (Function) — `research/jesse/jesse/helpers.py:331`
- **`np_ffill`** (Function) — `research/jesse/jesse/helpers.py:556`
- **`np_shift`** (Function) — `research/jesse/jesse/helpers.py:574`
- **`same_length`** (Function) — `research/jesse/jesse/helpers.py:805`
- **`slice_candles`** (Function) — `research/jesse/jesse/helpers.py:838`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `AccumulationDistributionOscillator` | Class | `research/Lean/Indicators/AccumulationDistributionOscillator.cs` | 25 |
| `AdvanceDeclineIndicator` | Class | `research/Lean/Indicators/AdvanceDeclineIndicator.cs` | 27 |
| `AverageDirectionalMovementIndexRating` | Class | `research/Lean/Indicators/AverageDirectionalMovementIndexRating.cs` | 24 |
| `AwesomeOscillator` | Class | `research/Lean/Indicators/AwesomeOscillator.cs` | 28 |
| `BalanceOfPower` | Class | `research/Lean/Indicators/BalanceOfPower.cs` | 24 |
| `ChandeKrollStop` | Class | `research/Lean/Indicators/ChandeKrollStop.cs` | 23 |
| `ChandeMomentumOscillator` | Class | `research/Lean/Indicators/ChandeMomentumOscillator.cs` | 24 |
| `ChoppinessIndex` | Class | `research/Lean/Indicators/ChoppinessIndex.cs` | 25 |
| `ConnorsRelativeStrengthIndex` | Class | `research/Lean/Indicators/ConnorsRelativeStrengthIndex.cs` | 27 |
| `CoppockCurve` | Class | `research/Lean/Indicators/CoppockCurve.cs` | 24 |
| `DetrendedPriceOscillator` | Class | `research/Lean/Indicators/DetrendedPriceOscillator.cs` | 25 |
| `DonchianChannel` | Class | `research/Lean/Indicators/DonchianChannel.cs` | 27 |
| `FisherTransform` | Class | `research/Lean/Indicators/FisherTransform.cs` | 38 |
| `ForceIndex` | Class | `research/Lean/Indicators/ForceIndex.cs` | 23 |
| `HurstExponent` | Class | `research/Lean/Indicators/HurstExponent.cs` | 26 |
| `InternalBarStrength` | Class | `research/Lean/Indicators/InternalBarStrength.cs` | 24 |
| `KnowSureThing` | Class | `research/Lean/Indicators/KnowSureThing.cs` | 24 |
| `LogReturn` | Class | `research/Lean/Indicators/LogReturn.cs` | 24 |
| `MarketProfile` | Class | `research/Lean/Indicators/MarketProfile.cs` | 38 |
| `MesaAdaptiveMovingAverage` | Class | `research/Lean/Indicators/MesaAdaptiveMovingAverage.cs` | 24 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Fills | 189 calls |
| Securities | 35 calls |
| Algorithm | 27 calls |
| Algorithm.CSharp | 25 calls |
| Data | 16 calls |
| Consolidators | 15 calls |
| Generic | 12 calls |
| DataFeeds | 7 calls |

## How to Explore

1. `gitnexus_context({name: "get_candle_source"})` — see callers and callees
2. `gitnexus_query({query: "indicators"})` — find related execution flows
3. Read key files listed above for implementation details
