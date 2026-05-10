# DeepSeek Operational Rules

## Reasoning Scale
- MAX Effort: ONLY for Trading Signal strategies, architectural shifts, and Flask/RQ async logic.
- HIGH Effort: Use for standard coding and bug fixes.
- LOW Effort: Use for CSS, UI tweaks, or documentation.

## Behavior
- Always run memory_search at the start of the session.
- Do NOT use the "6-gate" protocol from CLAUDE.md.
- If the task is LOW effort, do not use a "Thinking" block—just execute the code.
