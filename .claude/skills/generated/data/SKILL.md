---
name: data
description: "Skill for the Data area of Trading-Signals. 675 symbols across 173 files."
---

# Data

675 symbols | 173 files | Cohesion: 61%

## When to Use

- Working with code in `research/`
- Understanding how T, optionally, expect_dtypes work
- Modifying data-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Tests/Common/Data/SliceTests.cs` | AccessesBaseBySymbol, AccessesTradeBarBySymbol, EquitiesIgnoreQuoteBars, AccessesTradeBarCollection, AccessesTicksBySymbol (+23) |
| `research/zipline/zipline/data/minute_bars.py` | MinuteBarReader, _ohlc_ratio_inverse_for_sid, _minute_exclusion_tree, _find_position_of_minute, load_raw_arrays (+20) |
| `research/freqtrade/freqtrade/data/dataprovider.py` | refresh, ticker, orderbook, check_delisting, current_whitelist (+18) |
| `research/zipline/zipline/data/data_portal.py` | _is_extra_source, get_spot_value, get_adjustments, get_adjusted_value, _get_adjustment_list (+18) |
| `research/zipline/tests/data/test_daily_bars.py` | test_coerce_to_uint32_price, asset_start, test_start_on_asset_start, test_end_on_asset_start, test_unadjusted_get_value_no_data (+16) |
| `research/freqtrade/tests/data/test_dataprovider.py` | test_refresh, test_orderbook, test_ticker, test_no_exchange_mode, test_check_delisting (+15) |
| `research/zipline/zipline/data/hdf5_daily_bars.py` | coerce_to_uint32, write, _write_index_group, _write_lifetimes_group, _write_currency_group (+14) |
| `research/freqtrade/freqtrade/data/metrics.py` | create_cum_profit, calculate_cagr, calculate_expectancy, calculate_sqn, _prepare_balance_history (+14) |
| `research/Lean/Tests/Common/Data/TradeBarConsolidatorTests.cs` | ZeroCountAlwaysFires, OneCountAlwaysFires, TwoCountFiresEveryOther, ZeroSpanAlwaysThrows, ConsolidatesOHLCV (+13) |
| `research/freqtrade/tests/data/test_history.py` | test_load_data_1min_timeframe, test_load_data_mark, test_load_partial_missing, test_init_with_refresh, test_download_pair_history2 (+11) |

## Entry Points

Start here when exploring this area:

- **`T`** (Function) — `research/zipline/tests/data/test_adjustments.py:100`
- **`optionally`** (Function) — `research/zipline/zipline/utils/input_validation.py:88`
- **`expect_dtypes`** (Function) — `research/zipline/zipline/utils/input_validation.py:226`
- **`coerce_types`** (Function) — `research/zipline/zipline/utils/input_validation.py:803`
- **`preprocess`** (Function) — `research/zipline/zipline/utils/preprocess.py:34`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `TradeBarConsolidator` | Class | `research/Lean/Common/Data/Consolidators/TradeBarConsolidator.cs` | 29 |
| `Stochastic` | Class | `research/Lean/Indicators/Stochastic.cs` | 26 |
| `Slice` | Class | `research/Lean/Common/Data/Slice.cs` | 32 |
| `UnlinkedData` | Class | `research/Lean/Common/Data/Custom/IconicTypes/UnlinkedData.cs` | 27 |
| `TickConsolidator` | Class | `research/Lean/Common/Data/Consolidators/TickConsolidator.cs` | 25 |
| `BaseDataConsolidator` | Class | `research/Lean/Common/Data/Consolidators/BaseDataConsolidator.cs` | 24 |
| `HistoryRequest` | Class | `research/Lean/Common/Data/HistoryRequest.cs` | 27 |
| `TradingAlgorithm` | Class | `research/zipline/zipline/algorithm.py` | 149 |
| `Column` | Class | `research/zipline/zipline/pipeline/data/dataset.py` | 38 |
| `BoundColumn` | Class | `research/zipline/zipline/pipeline/data/dataset.py` | 135 |
| `MarketHourAwareConsolidator` | Class | `research/Lean/Common/Data/Consolidators/MarketHourAwareConsolidator.cs` | 27 |
| `DataQueueHandlerSubscriptionManager` | Class | `research/Lean/Common/Data/DataQueueHandlerSubscriptionManager.cs` | 27 |
| `EventBasedDataQueueHandlerSubscriptionManager` | Class | `research/Lean/Common/Data/EventBasedDataQueueHandlerSubscriptionManager.cs` | 26 |
| `FakeDataQueuehandlerSubscriptionManager` | Class | `research/Lean/Tests/Common/Data/FakeDataQueuehandlerSubscriptionManager.cs` | 21 |
| `TickQuoteBarConsolidator` | Class | `research/Lean/Common/Data/Consolidators/TickQuoteBarConsolidator.cs` | 25 |
| `FilteredIdentityDataConsolidator` | Class | `research/Lean/Common/Data/Consolidators/FilteredIdentityDataConsolidator.cs` | 25 |
| `IdentityDataConsolidator` | Class | `research/Lean/Common/Data/Consolidators/IdentityDataConsolidator.cs` | 25 |
| `BarReader` | Class | `research/zipline/zipline/data/bar_reader.py` | 42 |
| `InMemoryDailyBarReader` | Class | `research/zipline/zipline/data/in_memory_daily_bars.py` | 14 |
| `MinuteBarReader` | Class | `research/zipline/zipline/data/minute_bars.py` | 66 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Fills | 80 calls |
| Securities | 49 calls |
| Algorithm.CSharp | 32 calls |
| Exchange | 28 calls |
| Pipeline | 27 calls |
| Consolidators | 19 calls |
| Freqtradebot | 15 calls |
| Util | 12 calls |

## How to Explore

1. `gitnexus_context({name: "T"})` — see callers and callees
2. `gitnexus_query({query: "data"})` — find related execution flows
3. Read key files listed above for implementation details
