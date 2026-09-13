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

- **First Run**: If no blueprint exists in `workflows/`, the orchestrator will wake up the Discovery Agent (Claude) to learn the workflow. The terminal will log the thought process. You will be prompted to approve "risky actions" (like clicking Transact).
- **Subsequent Runs**: Once `workflows/mock_bank_tx.json` is generated, running `main.py` will completely bypass the LLM and execute the automation deterministically in under 3 seconds!

## Evidence
Check the `/evidence` folder for sample logs showcasing the Discovery Run, the successful Replay Run, the Graceful Error handling (business error), and the Hard Error escalation (human-in-the-loop).