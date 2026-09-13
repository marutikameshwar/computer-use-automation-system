# Computer-Use Automation System

An intelligent, self-healing automation system built to interact deterministically with web applications. This system separates the heavy, slow LLM logic (Discovery Phase) from the fast, deterministic execution (Replay Phase) to achieve robust, scalable, enterprise-grade automation.

## Features
- **LLM-Powered Discovery**: Uses Anthropic's Claude 3.5 to explore and learn workflows based purely on a natural language goal.
- **Deterministic Replay Engine**: Executes the discovered blueprint directly using Playwright, bypassing the LLM completely for 100% reliable, low-latency execution.
- **Human-in-the-Loop Escalation**: Gracefully pauses execution and prompts an operator if an unexpected UI change or error occurs.
- **Guardrails for Risky Actions**: Intercepts actions like "submit" or "transact" to prevent accidental modifications during unapproved discovery runs.
- **Business Error Detection**: Understands the difference between a broken UI and a legitimate business state (e.g., "Account not found").

## Setup Instructions

### 1. Requirements
- Python 3.10+
- Anthropic API Key (Claude 3.5 Sonnet/Haiku)

### 2. Installation
Clone the repository and install the requirements:
```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Variables
Create a `.env` file in the root directory and add your Anthropic API Key:
```env
ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Demo

### 1. Start the Mock Bank Application
In your first terminal, start the local mock application:
```bash
# Ensure your virtual environment is activated
python mock_app/app.py
```
The app will run on `http://localhost:5000`. Keep this terminal open.

### 2. Run the Orchestrator
In a second terminal, run the orchestrator:
```bash
# Ensure your virtual environment is activated
python main.py
```

The system will prompt you for a `Member ID`. Try the following three scenarios in order:

#### Scenario A: Happy Path & Discovery
- **Input:** `12345`
- **What happens:** If no blueprint exists in `workflows/`, the orchestrator wakes up the Discovery Agent (Claude) to learn the workflow. It navigates the UI, clicks Transact, enters 500, and extracts the receipt. You will be prompted to approve "risky actions" (hitting Enter in the terminal). 
- **Result:** It generates `v1.json` and a `current.txt` pointer. If you run `12345` again, it will bypass the LLM and execute the deterministic replay in under 3 seconds!

#### Scenario B: Business Error
- **Input:** `999`
- **What happens:** The deterministic Replay Engine tries to execute the `v1` capability but the app returns "Record not found". The engine times out trying to find the "Transact" button. It escalates to the AI `ClassificationAgent`, which recognizes the business error.
- **Result:** You approve the classification, and the system deep-copies `v1` into `v2.json`, storing `record_not_found` as a known `business_outcome`.

#### Scenario C: Hard Failure & Human Handoff
- **Input:** `500`
- **What happens (Run 1):** The app returns a 500 server crash page. The engine escalates to the AI. You approve the classification. The system saves `v3.json` with `server_crash` as a known `hard_failure`.
- **What happens (Run 2):** Run `python main.py` and enter `500` again. The engine hits the crash, but this time recognizes it as a *known hard failure*. It pauses execution and asks you to fix the browser state. 
- **The Handoff:** Click the "Resolve System Error" button on the 500 crash page (which bypasses you to the dashboard). Go back to your terminal and press **Enter**. The execution engine intrinsically retries the failed step and successfully completes the automation!

## Evidence
Check the `/evidence` folder for sample logs showcasing the Discovery Run, the successful Replay Run, the Graceful Error handling (business error), and the Hard Error escalation (human-in-the-loop).