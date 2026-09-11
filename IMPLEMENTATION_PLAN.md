# End-to-End Implementation Plan: Computer-Use Automation System

This document outlines the step-by-step plan to build the backend integration layer for the interface.ai take-home assessment. The tech stack will be Python, Playwright, and Claude 3.5 Sonnet (via Anthropic API).

## Phase 1: Project Setup & Scaffolding
- [ ] Initialize a new Git repository in the project folder.
- [ ] Set up a Python virtual environment (`python -m venv venv`).
- [ ] Install required dependencies: `playwright`, `anthropic`, `pydantic`, `pytest`, `python-dotenv`.
- [ ] Run `playwright install` to install browser binaries.
- [ ] Create the core folder structure:
  - `src/agent/` (LLM discovery loop)
  - `src/replay/` (Deterministic execution engine)
  - `src/schema/` (Pydantic models for the artifact)
  - `mock_app/` (The proxy local application)
  - `evidence/` (For the final deliverables)

## Phase 2: The Target Application (Mock App)
*Goal: Create a stable but "legacy" local target to avoid relying on public internet flakiness.*
- [ ] Build a simple local HTTP server (using Python's built-in `http.server` or a minimal `Flask` app).
- [ ] Create 3-4 HTML pages to represent a bank back-office:
  - Page 1: Member Search (Form with an intentional lack of clear CSS IDs).
  - Page 2: Member Dashboard (Nested tables containing account balances).
  - Page 3: Transaction form with a confirmation dialog.
- [ ] Build in a deterministic "Business Error" state (e.g., searching for member "999" always shows a "Record not found" banner).

## Phase 3: The Artifact Schema (Data Models)
*Goal: Define the strict contract between the discovery run and the replay run.*
- [ ] Create Pydantic models for the schema in `src/schema/models.py`.
- [ ] Define the `CapabilityArtifact` root object (version, name, inputs, outputs, success condition).
- [ ] Define the `Step` object (action type, locator, value).
- [ ] Define the `Locator` strategy focusing on Accessibility (Role/Name) and visual text, NOT raw CSS paths.
- [ ] Define how to represent Expected Business Outcomes (e.g., "Record not found") vs. Hard Failures.

## Phase 4: The Discovery Loop (LLM Agent)
*Goal: The agent observes the page, decides what to do, acts, and records the steps.*
- [ ] Create a Playwright controller wrapper to extract the page state (Accessibility Tree / simplified text representation).
- [ ] Initialize the Anthropic client with a strict system prompt instructing it to achieve the user's goal.
- [ ] Implement the `Observe -> Decide -> Act` loop:
  - Feed the page state to Claude.
  - Parse Claude's tool call (e.g., `click("button", "Submit")`).
  - Execute the action using Playwright.
  - Append the executed step to a running list of `Step` objects.
- [ ] Upon successful goal completion, serialize the steps, inputs, and outputs into the JSON `CapabilityArtifact` and save it to disk.

## Phase 5: The Deterministic Replay Engine
*Goal: Re-run the artifact JSON deterministically without the LLM.*
- [ ] Create an execution script that takes the saved `artifact.json` and input parameters.
- [ ] Implement a loop that iterates over the `Step`s in the artifact.
- [ ] Translate the schema `Locator`s into robust Playwright actions (e.g., `page.get_by_role()`, `page.get_by_text()`).
- [ ] Implement strict assertions and wait states (e.g., wait for network idle, wait for specific elements to appear) to handle transient slowness.
- [ ] Extract the required output data as defined in the schema.

## Phase 6: Error Handling & Human-in-the-Loop (Handoff)
*Goal: Fulfill the escalation and handoff requirements.*
- [ ] In the Replay engine, add a `try/except` block for timeouts and missing elements.
- [ ] If an action fails, check if the screen matches any defined "Expected Business Outcomes" (e.g., "Record not found"). If so, exit gracefully with a business outcome result.
- [ ] If it's a hard failure/stuck state, trigger the `escalate_to_human()` function:
  - Pause the Playwright script (`page.pause()` or a custom console prompt).
  - Dump a screenshot / DOM snapshot to the `evidence/` folder.
  - Display a mocked operator prompt in the terminal: "Agent stuck on step X. Please take control of the browser, fix the state, and press Enter to resume."
  - Resume the replay loop once the human hands control back.

## Phase 7: Safety & Guardrails
*Goal: Ensure the agent operates securely.*
- [ ] Implement a domain Allowlist (e.g., strictly `http://localhost:*`). Throw an error if the agent attempts to navigate elsewhere.
- [ ] Add a redaction utility: When dumping logs or saving the artifact, ensure any sensitive inputs (like a simulated SSN or password) are replaced with `[REDACTED]` in the output logs.

## Phase 8: Deliverables & Documentation
*Goal: Package the submission exactly as requested.*
- [ ] Run a clean discovery run and save the logs/artifact to the `/evidence/` folder.
- [ ] Run a successful replay run and save the logs.
- [ ] Run a replay run that intentionally hits a business error (e.g., bad input) and save the logs showing the correct detection.
- [ ] Write the `/README.md` with explicit setup instructions and demo commands.
- [ ] Write the `/REPORT.md` answering the 7 specific design questions (Architecture, Artifact schema, Determinism, Heterogeneity, Escalation, Safety, Cuts).
