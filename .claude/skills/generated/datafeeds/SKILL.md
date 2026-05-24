---
name: datafeeds
description: "Skill for the DataFeeds area of Trading-Signals. 739 symbols across 258 files."
---

# DataFeeds

739 symbols | 258 files | Cohesion: 61%

## When to Use

- Working with code in `research/`
- Understanding how AlgorithmStatusPacket, RealTimeProvider, FuncTextWriter work
- Modifying datafeeds-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/Lean/Tests/Engine/DataFeeds/LiveTradingDataFeedTests.cs` | FastExitsDoNotThrowUnhandledExceptions, HandlesAllTypes, HandlesFutureAndOptionChainUniverse, TestableLiveTradingDataFeed, TestDataChannelProvider (+67) |
| `research/Lean/Engine/DataFeeds/LiveTradingDataFeed.cs` | Initialize, HandleUnsupportedConfigurationEvent, IsExpired, GetWarmupEnumerator, CreateSubscription (+10) |
| `research/Lean/Tests/Engine/DataFeeds/SubscriptionCollectionTests.cs` | DefaultFillForwardResolution, UpdatesFillForwardResolutionOverridesDefaultWhenNotAdding, UpdatesFillForwardResolutionSuccessfullyWhenNotAdding, UpdatesFillForwardResolutionSuccessfullyWhenAdding, UpdatesFillForwardResolutionSuccessfullyOverridesDefaultWhenAdding (+9) |
| `research/Lean/Tests/Engine/DataFeeds/DataQueueHandlerManagerTests.cs` | SetJob, SubscribeReturnsNull, SubscribeReturnsNotNull, Unsubscribe, DoubleSubscribe (+8) |
| `research/Lean/Tests/Engine/DataFeeds/PendingRemovalsManagerTests.cs` | ReturnedRemoved_Add, ReturnedRemoved_Check, WontRemoveBecauseOfUnderlying, WontRemoveBecauseOpenOrder_Add, WontRemoveBecauseOpenOrder_Check (+7) |
| `research/Lean/Tests/Engine/DataFeeds/AggregationManagerTests.cs` | PassesTicksStraightThrough, BadTicksIgnored, TickTypeRespected, UnknownSubscriptionIgnored, CanHandleMultipleSubscriptions (+7) |
| `research/Lean/Engine/DataFeeds/ZipDataCacheProvider.cs` | Fetch, CacheAndCreateEntryStream, CreateEntryStream, Cache, GetZipEntries (+7) |
| `research/Lean/Tests/Engine/DataFeeds/TextSubscriptionDataSourceReaderTests.cs` | CachedDataIsReturnedAsClone, DataIsNotCachedForEphemeralDataCacheProvider, DataIsCachedForNonEphemeralDataCacheProvider, DataIsCachedCorrectly, CacheBehaviorDifferentResolutions (+7) |
| `research/Lean/Tests/Engine/DataFeeds/CustomLiveDataFeedTests.cs` | RunLiveDataFeed, TearDown, EmitsDailyCustomFutureDataOverWeekends, RemoteDataDoesNotIncreaseNumberOfSlices, LiveDataFeedSourcesDataFromObjectStoreSort (+6) |
| `research/Lean/Engine/DataFeeds/DateChangeTimeKeeper.cs` | SetUtcDateTime, AdvanceTowardsExchangeTime, TryAdvanceUntilNextDataDate, EmitFirstExchangeDate, SetExchangeTime (+6) |

## Entry Points

Start here when exploring this area:

- **`AlgorithmStatusPacket`** (Class) — `research/Lean/Common/Packets/AlgorithmStatusPacket.cs:24`
- **`RealTimeProvider`** (Class) — `research/Lean/Common/RealTimeProvider.cs:24`
- **`FuncTextWriter`** (Class) — `research/Lean/Common/Util/FuncTextWriter.cs:25`
- **`DataUniverseDownloadConfig`** (Class) — `research/Lean/DownloaderDataProvider/Models/DataUniverseDownloadConfig.cs:23`
- **`DataChannelProvider`** (Class) — `research/Lean/Engine/DataFeeds/DataChannelProvider.cs:28`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `AlgorithmStatusPacket` | Class | `research/Lean/Common/Packets/AlgorithmStatusPacket.cs` | 24 |
| `RealTimeProvider` | Class | `research/Lean/Common/RealTimeProvider.cs` | 24 |
| `FuncTextWriter` | Class | `research/Lean/Common/Util/FuncTextWriter.cs` | 25 |
| `DataUniverseDownloadConfig` | Class | `research/Lean/DownloaderDataProvider/Models/DataUniverseDownloadConfig.cs` | 23 |
| `DataChannelProvider` | Class | `research/Lean/Engine/DataFeeds/DataChannelProvider.cs` | 28 |
| `DataManager` | Class | `research/Lean/Engine/DataFeeds/DataManager.cs` | 33 |
| `LiveSynchronizer` | Class | `research/Lean/Engine/DataFeeds/LiveSynchronizer.cs` | 30 |
| `LiveTimeProvider` | Class | `research/Lean/Engine/DataFeeds/LiveTimeProvider.cs` | 23 |
| `UniverseSelection` | Class | `research/Lean/Engine/DataFeeds/UniverseSelection.cs` | 32 |
| `RegressionResultHandler` | Class | `research/Lean/Engine/Results/RegressionResultHandler.cs` | 38 |
| `IndicatorBasedOptionPriceModelProvider` | Class | `research/Lean/Indicators/IndicatorBasedOptionPriceModelProvider.cs` | 24 |
| `ConsoleLogHandler` | Class | `research/Lean/Logging/ConsoleLogHandler.cs` | 24 |
| `FuncDataQueueHandler` | Class | `research/Lean/Tests/Engine/DataFeeds/FuncDataQueueHandler.cs` | 35 |
| `SignerSink` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/crypto/io/SignerSink.cs` | 6 |
| `BaseInputStream` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/util/io/BaseInputStream.cs` | 5 |
| `BaseOutputStream` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/util/io/BaseOutputStream.cs` | 5 |
| `BaseDataExchange` | Class | `research/Lean/Engine/DataFeeds/BaseDataExchange.cs` | 30 |
| `EnqueueableEnumerator` | Class | `research/Lean/Engine/DataFeeds/Enumerators/EnqueueableEnumerator.cs` | 29 |
| `LiveCustomDataSubscriptionEnumeratorFactory` | Class | `research/Lean/Engine/DataFeeds/Enumerators/Factories/LiveCustomDataSubscriptionEnumeratorFactory.cs` | 30 |
| `TimeTriggeredUniverseSubscriptionEnumeratorFactory` | Class | `research/Lean/Engine/DataFeeds/Enumerators/Factories/TimeTriggeredUniverseSubscriptionEnumeratorFactory.cs` | 31 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Run → CreateMessage` | cross_community | 6 |
| `Main → Debug` | cross_community | 5 |
| `Main → Debug` | cross_community | 5 |
| `Main → Debug` | cross_community | 5 |
| `Main → Trace` | cross_community | 5 |
| `Main → Trace` | cross_community | 5 |
| `Main → Trace` | cross_community | 5 |
| `Main → Trace` | cross_community | 5 |
| `Main → Trace` | cross_community | 5 |
| `Main → Error` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Securities | 196 calls |
| Algorithm | 104 calls |
| Util | 61 calls |
| Algorithm.CSharp | 58 calls |
| Enumerators | 56 calls |
| Results | 36 calls |
| Fills | 31 calls |
| Brokerages | 29 calls |

## How to Explore

1. `gitnexus_context({name: "AlgorithmStatusPacket"})` — see callers and callees
2. `gitnexus_query({query: "datafeeds"})` — find related execution flows
3. Read key files listed above for implementation details
