---
name: tests
description: "Skill for the Tests area of Trading-Signals. 1188 symbols across 255 files."
---

# Tests

1188 symbols | 255 files | Cohesion: 67%

## When to Use

- Working with code in `research/`
- Understanding how trace, lp_0, lp_1 work
- Modifying tests-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/cvxpy/cvxpy/tests/solver_test_helpers.py` | solve, verify_objective, verify_primal_values, verify_dual_values, lp_0 (+61) |
| `research/vectorbt/tests/test_portfolio.py` | from_signals_both, from_signals_longonly, from_signals_shortonly, test_amount, test_value (+59) |
| `research/cvxpy/cvxpy/tests/test_problem.py` | test_transpose, test_expression_values, test_div, test_reshape, test_psd_duals (+48) |
| `research/cvxpy/cvxpy/tests/test_conic_solvers.py` | test_ecos_options, test_cvxopt_options, test_cplex_warm_start, test_gurobi_warm_start, test_xpress_warm_start (+45) |
| `research/cvxpy/cvxpy/tests/test_qp_solvers.py` | test_parametric, test_warm_start, test_qpalm_warmstart, test_xpress_warmstart, test_highs_warmstart (+41) |
| `research/cvxpy/cvxpy/tests/test_atoms.py` | test_reshape, test_diag_offset, test_sum_largest_axis, test_diff, test_flatten (+26) |
| `research/cvxpy/cvxpy/tests/test_derivative.py` | test_backward_real_and_imag, test_forward_complex_delta, test_param_used_in_exponent_and_elsewhere, perturbcheck, gradcheck (+25) |
| `research/zipline/tests/test_assets.py` | write_assets, country_code, test_lookup_symbol_delimited, shouldnt_resolve, test_lookup_symbol_fuzzy (+19) |
| `research/vectorbt/tests/test_records.py` | test_reduce, test_reduce_to_idx, test_reduce_to_array, test_reduce_to_idx_array, test_nth (+16) |
| `research/cvxpy/cvxpy/tests/test_grad.py` | test_partial_problem, positive, with_zero, generate, test_single_var_atom (+16) |

## Entry Points

Start here when exploring this area:

- **`trace`** (Function) — `research/cvxpy/cvxpy/atoms/affine/trace.py:27`
- **`lp_0`** (Function) — `research/cvxpy/cvxpy/tests/solver_test_helpers.py:259`
- **`lp_1`** (Function) — `research/cvxpy/cvxpy/tests/solver_test_helpers.py:268`
- **`mi_lp_1`** (Function) — `research/cvxpy/cvxpy/tests/solver_test_helpers.py:877`
- **`test_run`** (Function) — `research/backtrader/tests/test_analyzer-sqn.py:153`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Symbols` | Class | `research/Lean/Tests/Symbols.cs` | 27 |
| `testMainClass` | Class | `research/ccxt/cs/tests/BaseTest.Helpers.cs` | 14 |
| `BaseTest` | Class | `research/cvxpy/cvxpy/tests/base_test.py` | 22 |
| `TestFuzzReshapeNdInference` | Class | `research/cvxpy/cvxpy/tests/test_fuzz_reshape.py` | 90 |
| `TestKron` | Class | `research/cvxpy/cvxpy/tests/test_kron_canon.py` | 22 |
| `QPTestBase` | Class | `research/cvxpy/cvxpy/tests/test_qp_solvers.py` | 53 |
| `A` | Class | `research/vectorbt/tests/test_utils.py` | 1488 |
| `B` | Class | `research/vectorbt/tests/test_utils.py` | 1492 |
| `C` | Class | `research/vectorbt/tests/test_utils.py` | 1503 |
| `D` | Class | `research/vectorbt/tests/test_utils.py` | 1781 |
| `WithBarDataChecks` | Class | `research/zipline/tests/test_bar_data.py` | 62 |
| `TestMinuteBarData` | Class | `research/zipline/tests/test_bar_data.py` | 107 |
| `TestMinuteBarDataFuturesCalendar` | Class | `research/zipline/tests/test_bar_data.py` | 730 |
| `TestDailyBarData` | Class | `research/zipline/tests/test_bar_data.py` | 856 |
| `ExamplesTests` | Class | `research/zipline/tests/test_examples.py` | 41 |
| `JobQueue` | Class | `research/Lean/Queues/JobQueue.cs` | 36 |
| `JobQueueTestClass` | Class | `research/Lean/Tests/JobQueueTests.cs` | 49 |
| `DataPortalTestBase` | Class | `research/zipline/tests/test_data_portal.py` | 39 |
| `TestDataPortal` | Class | `research/zipline/tests/test_data_portal.py` | 579 |
| `TestDataPortalExplicitLastAvailable` | Class | `research/zipline/tests/test_data_portal.py` | 585 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Generic | 26 calls |
| Pipeline | 24 calls |
| Strategies | 18 calls |
| Efficient_frontier | 16 calls |
| Pypfopt | 10 calls |
| Jesse | 10 calls |
| Solvers | 9 calls |
| Freqtradebot | 9 calls |

## How to Explore

1. `gitnexus_context({name: "trace"})` — see callers and callees
2. `gitnexus_query({query: "tests"})` — find related execution flows
3. Read key files listed above for implementation details
