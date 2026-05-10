# Global Operational Protocol

## 1. Dynamic Reasoning Scale
- **MAX Effort:** Mandatory for architectural changes, async logic (Flask/RQ), trading signal strategies, and complex debugging.
- **HIGH Effort:** Use for writing tests, standard CRUD features, and code refactoring.
- **LOW Effort:** Use for documentation, simple CLI explanations, and UI/CSS tweaks.

## 2. Tool & MCP Utilization
- **Memory:** Always run memory_search at the start of a session.
- **Verification:** For backend logic, verify code via dry-runs or unit tests.

## 3. Communication
- Be direct and technical.
- For trading-signals-saas logs, prioritize root-cause analysis for worker/queue issues.
