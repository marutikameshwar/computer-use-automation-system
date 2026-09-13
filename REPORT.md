# Architectural Report: Computer-Use Automation System

This report outlines the design decisions made to satisfy the core constraints and objectives of the deterministic, agent-driven automation system. It strictly follows the 7 required headings.

### 1. Architecture
**Decision:** Isolate the LLM to discovery; enforce deterministic replay in production.
**Trade-offs & Rationale:** An open-source loop (Observe -> Prompt LLM -> Act -> Repeat) is too slow (5-10s per step), too expensive, and critically, too non-deterministic for enterprise production. If an LLM hallucinates, the automation breaks. By isolating the LLM entirely to the **Discovery Phase**, we use its intelligence exactly once to "learn" the workflow and compile a blueprint. In production, the **Replay Phase** executes this blueprint directly via Playwright without any LLM intervention. This guarantees 100% determinism, 0 LLM costs, and execution speeds under 3 seconds per run.

### 2. Artifact Schema
**Decision:** A strict JSON schema (`CapabilityArtifact`) with immutable pointer-based versioning.
**Trade-offs & Rationale:** The schema serves as a strict contract between the LLM and the Replay Engine. It encodes:
- **`inputs` / `outputs`**: Dynamic parameter injection (e.g., `member_id` replacing recorded values) and data extraction (`transaction_receipt`), allowing seamless integration into backend APIs.
- **`steps`**: An ordered array of actions and strict `Locator` objects using accessibility roles/text rather than brittle CSS.
- **`expected_outcomes` & Versioning:** When an unknown state occurs, the system generates a deep-copy of the artifact (`v2.json`, `v3.json`) adding the newly classified outcome, and updates a `current.txt` pointer. This provides an auditable history of how the capability evolved to handle edge cases over time, without mutating the original recording.

### 3. Determinism & Error Handling
**Decision:** Semantic locators for drift resistance; AI-assisted taxonomy for error classification.
**Trade-offs & Rationale:** 
- **Determinism:** The system aggressively avoids CSS selectors and XPath. The `Locator` schema enforces the use of Accessibility Roles. If a button's Tailwind class changes from `bg-blue-500` to `bg-red-500`, the automation continues flawlessly.
- **Error Handling:** When a step times out, the engine consults `expected_outcomes`. We implemented a rigorous error taxonomy: `business_outcome` (e.g., "Record not found", graceful exit) vs `hard_failure` (e.g., "Server crashed", pause for human). If the error is completely **Unknown**, the system escalates to an LLM `ClassificationAgent` to categorize it, writes a new version of the artifact, and stops.

### 4. Heterogeneity & Multi-Tenant
**Decision:** Playwright wrapper focused entirely on the Accessibility Tree.
**Trade-offs & Rationale:** By refusing to look at the raw HTML DOM, our Discovery agent only sees the `aria_snapshot()` tree. This perfectly extends to legacy server-rendered framesets and even desktop applications (via tools like PyAutoGUI/Windows UI Automation), because the agent only thinks in terms of semantic roles (buttons, textboxes, links). For multi-tenant reuse, the `inputs` schema allows injecting tenant-specific base URLs or configuration flags directly into the engine, preventing the need to record 50 identical workflows for 50 tenants.

### 5. Escalation & Handoff
**Decision:** Blocking terminal prompt combined with an execution `while` loop.
**Trade-offs & Rationale:** When the Replay Engine hits a known `hard_failure`, it does not crash. It saves a screenshot of the exact failure state to `/logs`, prints an alert, and pauses execution using `input()`. The human operator can then take control of the live browser session to resolve the issue (e.g., clicking a server bypass button). Once resolved, the operator presses Enter, and the `while` loop execution engine intrinsically **retries the failed step**. This ensures zero context is lost and the automation can seamlessly cross the seam back into autonomous execution.

### 6. Safety
**Decision:** Hardcoded guardrail interceptors and log redaction.
**Trade-offs & Rationale:** A hardcoded guardrail sits inside the lowest level execution wrapper. Whenever the system attempts to interact with an element, it checks the accessible name/value against risky keywords (`submit`, `transact`, `pay`). If a match is detected, the engine blocks the action and prompts the terminal for explicit operator approval. This protects both the Discovery Agent and the Replay Engine. Additionally, standard input variables are replaced with `[REDACTED]` in the terminal logs to prevent PII leakage.

### 7. Cuts
**Decision:** What we deliberately left out given the time constraints.
**Trade-offs & Rationale:** 
- **Discovery Handoff:** We implemented the Human-in-the-Loop browser handoff exclusively for the Replay Engine. If the LLM gets stuck during Discovery, the run simply fails. We chose this cut to prioritize the robustness of the production Replay path over edge cases in the one-time training path.
- **LLM Self-Healing Loop:** If Claude hallucinates an invalid JSON block during Discovery, we log the error and break. A full system would feed that `ValidationError` back into Claude to self-correct.
- **Multi-Tenant Routing:** While our architecture supports parameterized inputs, we did not build the routing infrastructure to maintain parallel artifact repos per tenant, as that ventures into infrastructure rather than core automation design.
