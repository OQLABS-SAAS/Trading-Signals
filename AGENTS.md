<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Trading-Signals** (712749 symbols, 1858109 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Trading-Signals/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Trading-Signals/clusters` | All functional areas |
| `gitnexus://repo/Trading-Signals/processes` | All execution flows |
| `gitnexus://repo/Trading-Signals/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |
| Work in the V4 area (13845 symbols) | `.claude/skills/generated/v4/SKILL.md` |
| Work in the Pro area (11822 symbols) | `.claude/skills/generated/pro/SKILL.md` |
| Work in the Ccxt area (5135 symbols) | `.claude/skills/generated/ccxt/SKILL.md` |
| Work in the Async_support area (3291 symbols) | `.claude/skills/generated/async-support/SKILL.md` |
| Work in the Browser area (2909 symbols) | `.claude/skills/generated/browser/SKILL.md` |
| Work in the Base area (2734 symbols) | `.claude/skills/generated/base/SKILL.md` |
| Work in the Async area (2581 symbols) | `.claude/skills/generated/async/SKILL.md` |
| Work in the Php area (2504 symbols) | `.claude/skills/generated/php/SKILL.md` |
| Work in the Exchanges area (2233 symbols) | `.claude/skills/generated/exchanges/SKILL.md` |
| Work in the Omni_files area (1367 symbols) | `.claude/skills/generated/omni-files/SKILL.md` |
| Work in the Securities area (1324 symbols) | `.claude/skills/generated/securities/SKILL.md` |
| Work in the Tests area (1188 symbols) | `.claude/skills/generated/tests/SKILL.md` |
| Work in the _nuxt area (1167 symbols) | `.claude/skills/generated/nuxt/SKILL.md` |
| Work in the Abstract area (1139 symbols) | `.claude/skills/generated/abstract/SKILL.md` |
| Work in the Indicators area (957 symbols) | `.claude/skills/generated/indicators/SKILL.md` |
| Work in the Algorithm area (956 symbols) | `.claude/skills/generated/algorithm/SKILL.md` |
| Work in the Algorithm.CSharp area (845 symbols) | `.claude/skills/generated/algorithm-csharp/SKILL.md` |
| Work in the DataFeeds area (739 symbols) | `.claude/skills/generated/datafeeds/SKILL.md` |
| Work in the Timeseries area (693 symbols) | `.claude/skills/generated/timeseries/SKILL.md` |
| Work in the Data area (675 symbols) | `.claude/skills/generated/data/SKILL.md` |

<!-- gitnexus:end -->
