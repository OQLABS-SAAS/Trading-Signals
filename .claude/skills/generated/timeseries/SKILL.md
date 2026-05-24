---
name: timeseries
description: "Skill for the Timeseries area of Trading-Signals. 693 symbols across 61 files."
---

# Timeseries

693 symbols | 61 files | Cohesion: 74%

## When to Use

- Working with code in `research/`
- Understanding how log_debug, build_eq_vol_scenario_intraday, build_eq_vol_scenario_eod work
- Modifying timeseries-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/gs-quant/gs_quant/timeseries/measures.py` | _asset_from_spec, _cross_stored_direction_helper, cross_stored_direction_for_fx_vol, cross_to_usd_based_cross, currency_to_default_benchmark_rate (+125) |
| `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | test_swap_rate_calc, test_check_clearing_house, test_match_floating_tenors, test_get_tdapi_rates_assets, test_get_swap_leg_defaults (+102) |
| `research/gs-quant/gs_quant/timeseries/measures_rates.py` | get_swaption_parameter, _pricing_location_normalized, _default_pricing_location, _cross_to_fxfwd_xcswp_asset, _currency_to_tdapi_swap_rate_asset (+56) |
| `research/gs-quant/gs_quant/timeseries/measures_reports.py` | thematic_exposure, thematic_beta, aum, hit_rate, portfolio_max_drawdown (+42) |
| `research/gs-quant/gs_quant/timeseries/measures_portfolios.py` | portfolio_hit_rate, portfolio_max_drawdown, portfolio_drawdown_length, portfolio_max_recovery_period, portfolio_standard_deviation (+30) |
| `research/gs-quant/gs_quant/timeseries/statistics.py` | rolling_std, _concat_series, min_, max_, range_ (+30) |
| `research/gs-quant/gs_quant/test/timeseries/test_measures_rates.py` | test_parse_meeting_date, test_swaption_vol2_return_data, test_swaption_annuity_return_data, test_swaption_premium_return_data, test_swaption_atmFwdRate_return_data (+22) |
| `research/gs-quant/gs_quant/timeseries/econometrics.py` | beta, get_ratio_pure, returns, prices, _get_annualization_factor (+13) |
| `research/gs-quant/gs_quant/timeseries/measures_fx_vol.py` | _currencypair_to_tdapi_fxfwd_asset, _currencypair_to_tdapi_fxo_asset, _currencypair_to_tdapi_fx_vol_swap_asset, _get_tdapi_fxo_assets, get_fxo_asset (+10) |
| `research/gs-quant/gs_quant/timeseries/backtesting.py` | backtest_basket, basket_series, _reset, get_marquee_ids, _ensure_spot_data (+9) |

## Entry Points

Start here when exploring this area:

- **`log_debug`** (Function) — `research/gs-quant/gs_quant/data/log.py:19`
- **`build_eq_vol_scenario_intraday`** (Function) — `research/gs-quant/gs_quant/risk/scenario_utils.py:23`
- **`build_eq_vol_scenario_eod`** (Function) — `research/gs-quant/gs_quant/risk/scenario_utils.py:40`
- **`test_build_market_data_query`** (Function) — `research/gs-quant/gs_quant/test/data/test_query.py:24`
- **`test_get_asset`** (Function) — `research/gs-quant/gs_quant/test/markets/test_securities.py:41`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ExtendedSeries` | Class | `research/gs-quant/gs_quant/timeseries/measures.py` | 88 |
| `log_debug` | Function | `research/gs-quant/gs_quant/data/log.py` | 19 |
| `build_eq_vol_scenario_intraday` | Function | `research/gs-quant/gs_quant/risk/scenario_utils.py` | 23 |
| `build_eq_vol_scenario_eod` | Function | `research/gs-quant/gs_quant/risk/scenario_utils.py` | 40 |
| `test_build_market_data_query` | Function | `research/gs-quant/gs_quant/test/data/test_query.py` | 24 |
| `test_get_asset` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 41 |
| `test_asset_identifiers` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 122 |
| `test_get_security` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 223 |
| `test_get_security_fields` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 302 |
| `test_secmaster_get_asset_no_asset_id_response_should_fail` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 1006 |
| `test_secmaster_get_asset_returning_secmasterassets` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 1043 |
| `assert_asset_common` | Function | `research/gs-quant/gs_quant/test/markets/test_securities.py` | 1044 |
| `test_basket_average_implied_vol` | Function | `research/gs-quant/gs_quant/test/timeseries/test_backtesting.py` | 188 |
| `test_basket_average_realized_vol_wts` | Function | `research/gs-quant/gs_quant/test/timeseries/test_backtesting.py` | 350 |
| `test_basket_average_realized_corr` | Function | `research/gs-quant/gs_quant/test/timeseries/test_backtesting.py` | 403 |
| `test_swap_rate_calc` | Function | `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | 440 |
| `test_check_clearing_house` | Function | `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | 579 |
| `test_match_floating_tenors` | Function | `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | 613 |
| `test_get_tdapi_rates_assets` | Function | `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | 729 |
| `test_get_swap_leg_defaults` | Function | `research/gs-quant/gs_quant/test/timeseries/test_measures.py` | 779 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Gs | 33 calls |
| Markets | 23 calls |
| Entities | 17 calls |
| Api | 7 calls |
| Data | 6 calls |
| Models | 4 calls |
| Datetime | 2 calls |
| Processors | 1 calls |

## How to Explore

1. `gitnexus_context({name: "log_debug"})` — see callers and callees
2. `gitnexus_query({query: "timeseries"})` — find related execution flows
3. Read key files listed above for implementation details
