---
name: browser
description: "Skill for the Browser area of Trading-Signals. 2909 symbols across 440 files."
---

# Browser

2909 symbols | 440 files | Cohesion: 69%

## When to Use

- Working with code in `research/`
- Understanding how findLast, createCancelablePromise, createCancelableAsyncIterable work
- Modifying browser-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/browser/dom.js` | registerWindow, getWindow, clearNode, addDisposableListener, _wrapAsStandardMouseEvent (+80) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/suggest/browser/suggestWidget.js` | applyIconStyle, applyStatusBarStyle, _layout, getLayoutInfo, forceRenderingAbove (+43) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/browser/coreCommands.js` | runEditorCommand, constructor, runCoreEditorCommand, runCoreEditorCommand, _move (+40) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/wordOperations/browser/wordOperations.js` | runEditorCommand, result, _moveTo, runEditorCommand, _delete (+36) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/folding/browser/folding.js` | constructor, constructor, constructor, constructor, constructor (+34) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/snippet/browser/snippetParser.js` | SnippetParser, escape, tokenText, next, appendChild (+31) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/find/browser/findController.js` | getSelectionSearchString, get, getState, _start, moveToNextMatch (+30) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/multicursor/browser/multicursor.js` | announceCursorChange, run, run, getCursorsForSelection, run (+30) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/browser/widget/codeEditor/codeEditorWidget.js` | invokeWithinContext, getOptions, getOption, getConfiguredWordAtPosition, _getVerticalOffsetAfterPosition (+29) |
| `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/event.js` | _addLeakageTraceLogic, any, snapshot, debounce, buffer (+28) |

## Entry Points

Start here when exploring this area:

- **`findLast`** (Function) — `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/arraysFind.js:4`
- **`createCancelablePromise`** (Function) — `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/async.js:13`
- **`createCancelableAsyncIterable`** (Function) — `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/async.js:823`
- **`cancelOnDispose`** (Function) — `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/cancellation.js:109`
- **`buildReplaceStringWithCasePreserved`** (Function) — `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/search.js:5`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `CancelableAsyncIterableObject` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/async.js` | 814 |
| `CancellationTokenSource` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/cancellation.js` | 67 |
| `StopWatch` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/base/common/stopwatch.js` | 5 |
| `TextAreaState` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/browser/controller/textAreaState.js` | 7 |
| `DisposableCancellationTokenSource` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/browser/widget/diffEditor/utils.js` | 309 |
| `ReplaceCommandThatPreservesSelection` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/commands/replaceCommand.js` | 66 |
| `Position` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/core/position.js` | 7 |
| `Range` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/core/range.js` | 8 |
| `Selection` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/core/selection.js` | 10 |
| `SingleTextEdit` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/core/textEdit.js` | 59 |
| `CursorPosition` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/cursor/cursorMoveOperations.js` | 10 |
| `CursorState` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/cursorCommon.js` | 147 |
| `SingleCursorState` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/cursorCommon.js` | 190 |
| `BracketPairGuidesClassNames` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/model/guidesTextModelPart.js` | 390 |
| `SearchParams` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/model/textModelSearch.js` | 10 |
| `InlineDecoration` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/viewModel.js` | 60 |
| `ViewModelDecoration` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/common/viewModel.js` | 78 |
| `EditorStateCancellationTokenSource` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/editorState/browser/editorState.js` | 68 |
| `TextModelCancellationTokenSource` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/editorState/browser/editorState.js` | 102 |
| `EditorKeybindingCancellationTokenSource` | Class | `research/jesse/jesse/static/_nuxt/nuxt-monaco-editor/vs/editor/contrib/editorState/browser/keybindingCancellation.js` | 52 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Cursor | 40 calls |
| ViewModel | 35 calls |
| List | 30 calls |
| Tree | 30 calls |
| Model | 27 calls |
| Actionbar | 25 calls |
| Controller | 25 calls |
| DiffEditor | 24 calls |

## How to Explore

1. `gitnexus_context({name: "findLast"})` — see callers and callees
2. `gitnexus_query({query: "browser"})` — find related execution flows
3. Read key files listed above for implementation details
