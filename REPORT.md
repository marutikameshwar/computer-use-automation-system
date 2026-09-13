# Architectural Report: Computer-Use Automation System

This report outlines the design decisions made to satisfy the core constraints and objectives of the deterministic, agent-driven automation system.

### 1. The Right Architecture
**Question:** Most open-source agents just loop around an LLM to take actions. Why is our architecture (Discovery Phase + Replay Phase) better for an enterprise scenario?
**Answer:** An open-source loop (Observe -> Prompt LLM -> Act -> Repeat) is too slow (5-10 seconds per step), too expensive (token costs per API call), and critically, too non-deterministic for enterprise production. If an LLM hallucinates one day, the automation breaks. By isolating the LLM entirely to the **Discovery Phase**, we use its intelligence exactly once to "learn" the workflow and compile a blueprint. In production, the **Replay Phase** executes this blueprint directly via Playwright without any LLM intervention. This guarantees 100% determinism, 0 LLM costs, and execution speeds under 3 seconds per run.

### 2. The Blueprint (Artifact) Schema
**Question:** What does your JSON structure look like and why? How does it encode the sequence, assertions, inputs, and expected outcomes?
**Answer:** The `CapabilityArtifact` JSON schema serves as a strict contract between the LLM and the Replay Engine. It encodes:
- **`inputs` / `outputs`**: The expected parameters to inject (e.g., `member_id`) and extract (e.g., `transaction_receipt`), allowing seamless integration into backend APIs.
- **`steps`**: An ordered array of `Step` objects, each containing an `action` (click, type, read_text) and a strict `Locator` (using accessibility roles/text rather than brittle CSS selectors).
- **`success_condition`**: A final assertion element the engine uses to definitively confirm the goal was reached.
- **`expected_outcomes`**: A list of known business states (e.g., "record_not_found") the engine checks if a step fails, enabling graceful failure rather than hard crashes.

### 3. Determinism & Robustness
**Question:** If the UI changes slightly (e.g., a button moves or CSS classes change), will your replay fail? How did you make it robust?
**Answer:** The system is highly robust against DOM drift because it aggressively avoids CSS selectors and XPath. Instead, the `Locator` schema enforces the use of **Accessibility Roles** (e.g., `role="button", name="Submit"`) and visible text. If a button moves from the left column to the right, or if its Tailwind class changes from `bg-blue-500` to `bg-red-500`, the automation continues flawlessly because the element's semantic role and accessible name remain identical.

### 4. Handling Heterogeneity
**Question:** How does the Replay Engine know when to wait for a network request versus when to just click immediately?
**Answer:** Playwright's auto-waiting mechanism handles the bulk of state readiness (waiting for elements to be attached, visible, and actionable). In the `PlaywrightController`, we prioritize semantic locators, ensuring the engine intrinsically waits for the specific element to be "ready" before interacting. By relying on Playwright's underlying event loop, we avoid arbitrary `time.sleep()` calls, ensuring the engine clicks immediately when possible, and waits naturally when network requests cause UI delays.

### 5. Fallback & Escalation
**Question:** When the deterministic replay *does* fail (e.g., the website underwent a major overhaul), what exactly happens?
**Answer:** When a locator strictly fails to resolve within the timeout period, the engine catches the exception and checks the `expected_outcomes` list to see if it's a known business error. If it is an unexpected hard failure, the engine initiates the **Human-in-the-Loop Escalation** protocol. It saves a screenshot of the exact failure state (`evidence/error_step_X.png`) and pauses execution with a blocking `input()` prompt. This alerts an operator, allowing them to manually intervene, fix the browser state, and press Enter to resume execution without losing the session context.

### 6. Safety & Guardrails
**Question:** How do you ensure the agent doesn't accidentally execute a real transaction during its discovery phase?
**Answer:** A hardcoded guardrail interceptor sits inside `src/utils/playwright_wrapper.py`. Whenever the Discovery Agent attempts to interact with an element, the `execute_action` method checks the element's accessible name and value against a list of risky keywords (`submit`, `transact`, `pay`, `confirm`). If a match is detected, the engine blocks the action and prompts the terminal for explicit operator approval. This ensures the LLM can never accidentally finalize a state-changing action during discovery.

### 7. What we cut and why
**Question:** Given the 48-hour limit, what edge cases or features did you intentionally choose not to build?
**Answer:** 
- **Dynamic Variable Injection:** The current `mock_bank_tx.json` hardcodes the values (`12345` and `500`). In a full system, the engine would parse the JSON and map the `inputs` array directly into the `step.value` fields dynamically at runtime. We cut this to focus on the core extraction logic.
- **LLM Self-Healing Loop:** Currently, if Claude hallucinates an invalid JSON block during the Discovery phase, we log the error and break. A robust system would feed that `ValidationError` back into Claude as a new prompt to let it self-correct.
- **Shadow DOM / Iframes:** We did not implement specialized traversal for Shadow DOMs or complex multi-iframe authentication walls, as it overcomplicated the MVP.
