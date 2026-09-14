# Computer-Use Automation System

An intelligent, self-healing automation system built to interact deterministically with web applications. 

Traditional UI automation scripts break easily when the UI changes, and pure LLM-based web agents are too slow, unreliable, and expensive for enterprise-scale execution. This system bridges the gap by separating the slow, intelligent learning process (**Discovery Phase**) from the lightning-fast, robust execution process (**Replay Phase**).

## 🌟 Core Features

- **LLM-Powered Discovery**: Uses Anthropic's Claude 3.5 Sonnet to autonomously explore, interact with, and map out workflows based entirely on a natural language goal.
- **Deterministic Replay Engine**: Executes the discovered blueprint directly using Playwright. Bypasses the LLM completely for 100% reliable, low-latency execution (sub-3 seconds).
- **Human-in-the-Loop (HITL)**: Gracefully pauses execution and prompts an operator for manual intervention if an unexpected UI state or hard error occurs, then resumes automatically.
- **Business Error Detection**: Can distinguish between a broken UI script and a legitimate application state (e.g., "Account not found" or "Insufficient Funds"), categorizing them correctly.
- **Guardrails for Risky Actions**: Intercepts potentially destructive actions (like "submit", "transfer", "delete") to prompt for manual approval during unapproved discovery runs.
- **Domain Allowlisting**: Prevents the agent from wandering off to unauthorized websites.

---

## 🛠️ Setup Instructions

### 1. Prerequisites
- **Python 3.10+** installed on your system.
- An **Anthropic API Key** (Claude 3.5 Sonnet is heavily recommended for best results).
- Git.

### 2. Installation
Clone the repository to your local machine:
```bash
git clone https://github.com/marutikameshwar/computer-use-automation-system.git
cd computer-use-automation-system
```

Create and activate a Python virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Mac/Linux
source venv/bin/activate
```

Install the required dependencies and browsers:
```bash
# Install python packages
pip install -r requirements.txt

# Install Playwright browser binaries (Chromium)
playwright install chromium
```

### 3. Environment Configuration
Create a `.env` file in the root directory of the project and add your Anthropic API Key:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
```

You can optionally tweak execution parameters like token limits, delays, and maximum steps in `config.yaml`.

---

## 🧪 Running the Test Suite
This project comes with a robust, production-level test suite boasting **86%+ code coverage**.
You can run the full suite using `pytest`:
```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```
The test suite utilizes mocked Anthropic API responses and mocked Playwright controllers to ensure tests execute quickly without launching actual browser windows.

---

## 🚀 Running the Application & Edge Cases

The project comes with a local Mock Bank application (`mock_app/app.py`) to safely demonstrate the system's capabilities, including its self-healing and error-handling edge cases.

### Step 1: Start the Mock Bank Application
In your first terminal (with the venv activated), start the local mock application:
```bash
python mock_app/app.py
```
The app will run locally on `http://localhost:5000`. **Keep this terminal open.**

### Step 2: Run the Orchestrator
In a second terminal, activate the virtual environment and run the orchestrator script. 

To run the application, you can optionally supply a custom starting link and a natural language prompt (goal). However, running it without arguments defaults to our built-in demo configuration:

```bash
python main.py --url "http://localhost:5000" --goal "Search for member 12345, navigate to their dashboard, initiate a savings transaction of 500, reach the confirmation page, extract the full text of the paragraph that starts with 'Successfully processed' into a variable named 'transaction_receipt', and then immediately output an action of wait with a value of DONE."
```

**Here is exactly how the system behaves, step-by-step:**

### 🟢 Run 1: The Initial Discovery Phase (Automatic Happy Path)
When you run `python main.py` for the very first time, the system notices that it does not have a blueprint for this task yet.
1. It automatically wakes up the **Discovery Agent** (powered by Claude).
2. It automatically uses the built-in default goal prompt:
   > *"Search for member 12345, navigate to their dashboard, initiate a savings transaction of 500, reach the confirmation page, extract the full text of the paragraph that starts with 'Successfully processed' into a variable named 'transaction_receipt', and then immediately output an action of wait with a value of DONE."*
3. Claude navigates the UI, clicks Transact, enters $500, and extracts the receipt.
4. *Safety Guardrail:* The terminal will pause and prompt you to approve a "risky action" before submitting the transaction. **Press Enter to approve.**
5. **The Result:** The LLM successfully learns the workflow. A deterministic execution blueprint is generated and permanently saved to `src/workflows/mock_bank_tx/v1.json`.

### ⚡ Run 2 & Beyond: Deterministic Replay & Edge Cases
Once the blueprint is saved, **every subsequent run completely bypasses the LLM.** 

The orchestrator now enters an infinite, interactive loop. The terminal will continuously prompt you:
`Enter Member ID (e.g. 12345, 999, 500, 888, 'q' to quit): `

From here, you can seamlessly enter different numbers to test various edge case scenarios without restarting the script:

#### 🟡 Scenario A: Business Error Recognition (Input: `999`)
- **Input (First attempt):** Type `999` and press Enter.
- **What happens:** 
  1. The **Replay Engine** blindly attempts to execute the `v1.json` blueprint (searching for the dashboard).
  2. The mock bank returns a "Record not found" error on the screen.
  3. The Replay Engine times out looking for the Transact button. It realizes the UI is stuck, so it escalates the failure to the **Classification Agent**.
  4. The Classification Agent analyzes the screen and categorizes this as a legitimate business error (a known application state), *not* a system bug.
- **The Result:** The system deep-copies the blueprint into `v2.json`, officially cataloging `record_not_found` as an expected `business_outcome`. 
- **Input (Second attempt):** Type `999` again.
- **What happens:** The system instantly matches the UI state to the `record_not_found` outcome in `v2.json` and gracefully exits *without* calling the LLM!

#### 🟠 Scenario B: Recoverable UI Change (Input: `888`)
- **Input:** Type `888` and press Enter.
- **What happens:** 
  1. A new, unexpected "Terms of Service" popup blocks the dashboard.
  2. The engine times out trying to click "Transact" because the popup is in the way. It escalates to the AI.
  3. The Classification Agent identifies this as a `recoverable_condition` and instructs the engine to click "Acknowledge & Close".
- **The Result:** The engine clicks the popup away, seamlessly resumes the original automation, and successfully completes the transaction!

#### 🔴 Scenario C: Hard System Failure & Human Handoff (Input: `500`)
- **Input (First attempt):** Type `500` and press Enter.
- **What happens:** 
  1. The app throws a simulated 500 Server Crash page.
  2. The engine escalates to the AI, which correctly identifies this as a catastrophic `hard_failure` (System Crash). 
  3. The system generates `v3.json`, logging this as a known critical failure.
- **Input (Second attempt):** Without restarting the script, type `500` at the prompt again. 
- **What happens:** 
  1. The engine hits the crash, but this time recognizes it immediately as a *known hard failure* from `v3.json`. 
  2. **Human-in-the-Loop:** It pauses execution and asks you via the terminal to manually fix the browser state!
- **The Recovery:** Go to the Chromium browser window that opened, click the **"Resolve System Error"** button to bypass the crash, return to your terminal, and press **Enter**. The deterministic engine will seamlessly resume execution right where it left off and successfully complete the automation!

---

## 📂 Project Structure

- `src/agent/` - Contains the AI Agents (`DiscoveryAgent`, `ClassificationAgent`) powered by Anthropic.
- `src/replay/` - The deterministic, lightning-fast execution engine and JSON writer.
- `src/browser/` - Playwright bindings, screenshots, accessibility tree parsing, and safety guardrails.
- `src/schema/` - Pydantic definitions for capability artifacts and data structures.
- `tests/` - The comprehensive Pytest suite mirroring the `src/` directory.
- `mock_app/` - The dummy Flask application used for demonstrations and test scenarios.