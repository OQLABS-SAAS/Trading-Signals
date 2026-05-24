---
name: omni-files
description: "Skill for the Omni_files area of Trading-Signals. 1367 symbols across 10 files."
---

# Omni_files

1367 symbols | 10 files | Cohesion: 70%

## When to Use

- Working with code in `research/`
- Understanding how rust_call, zklink_main_net_url, zklink_test_net_url work
- Modifying omni_files-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-x86.py` | write, write, write, write, write (+337) |
| `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py` | write, write, write, write, write (+337) |
| `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py` | write, write, write, write, write (+332) |
| `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk.py` | write, write, write, write, write (+332) |
| `research/ccxt/python/ccxt/static_dependencies/ethereum/abi/exceptions.py` | EncodingError, IllegalValue, DecodingError |
| `research/yfinance/yfinance/exceptions.py` | YFException, YFTickerMissingError |
| `research/ccxt/go/v4/exchange.go` | Exception |
| `research/ccxt/python/ccxt/static_dependencies/ecdsa/numbertheory.py` | Error |
| `research/hummingbot/hummingbot/exceptions.py` | HummingbotBaseException |
| `research/zipline/zipline/data/bar_reader.py` | NoDataOnDate |

## Entry Points

Start here when exploring this area:

- **`rust_call`** (Function) — `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-x86.py:251`
- **`zklink_main_net_url`** (Function) — `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py:7884`
- **`zklink_test_net_url`** (Function) — `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py:7888`
- **`zklink_main_net_url`** (Function) — `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py:7982`
- **`zklink_test_net_url`** (Function) — `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py:7986`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Error` | Class | `research/ccxt/python/ccxt/static_dependencies/ecdsa/numbertheory.py` | 18 |
| `EncodingError` | Class | `research/ccxt/python/ccxt/static_dependencies/ethereum/abi/exceptions.py` | 5 |
| `IllegalValue` | Class | `research/ccxt/python/ccxt/static_dependencies/ethereum/abi/exceptions.py` | 22 |
| `DecodingError` | Class | `research/ccxt/python/ccxt/static_dependencies/ethereum/abi/exceptions.py` | 55 |
| `HummingbotBaseException` | Class | `research/hummingbot/hummingbot/exceptions.py` | 5 |
| `EthSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py` | 6176 |
| `SignError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py` | 6667 |
| `StarkSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-arm.py` | 6734 |
| `EthSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py` | 6250 |
| `SignError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py` | 6741 |
| `StarkSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-pc.py` | 6808 |
| `TypeError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-x86.py` | 5086 |
| `EthSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk.py` | 6209 |
| `SignError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk.py` | 6700 |
| `StarkSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk.py` | 6767 |
| `YFException` | Class | `research/yfinance/yfinance/exceptions.py` | 0 |
| `YFTickerMissingError` | Class | `research/yfinance/yfinance/exceptions.py` | 14 |
| `NoDataOnDate` | Class | `research/zipline/zipline/data/bar_reader.py` | 17 |
| `EthSignerError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-x86.py` | 4747 |
| `CustomError` | Class | `research/jesse/jesse/modes/import_candles_mode/drivers/Apex/omni_files/zklink_sdk-x86.py` | 4815 |

## Connected Areas

| Area | Connections |
|------|-------------|
| V4 | 1 calls |

## How to Explore

1. `gitnexus_context({name: "rust_call"})` — see callers and callees
2. `gitnexus_query({query: "omni_files"})` — find related execution flows
3. Read key files listed above for implementation details
