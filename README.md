# Computer-Use Automation System

This project is a backend integration layer that enables AI agents to reliably and deterministically operate legacy back-office applications without APIs.

## 1. Setup Instructions

### Environment Setup
Create and activate a Python virtual environment:
```powershell
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies
Install the required Python packages and the necessary Playwright browser binaries:
```powershell
pip install -r requirements.txt
playwright install chromium
```

### API Keys
Create a `.env` file in the root directory and add your Anthropic API key (this will be required for the AI Discovery Agent):
```env
ANTHROPIC_API_KEY=your_key_here
```

---

## 2. The Target Application (Mock Bank)

Because we cannot safely or legally automate against real bank software, this repository includes a local Python Flask application (`mock_app/app.py`) that acts as our proxy target. 

It is intentionally designed to mimic "hostile" legacy software (e.g., using nested table-based layouts, missing CSS IDs, and no semantic data tags) to prove the AI agent's robustness.

### Starting the Target Application
To start the mock application, run:
```powershell
python mock_app/app.py
```
The server will run locally at `http://localhost:5000`.

### Built-in Testing Scenarios
The mock application contains hardcoded member IDs designed to test the specific edge cases required by the assignment. Enter these IDs on the search page to test the different flows:

- **`12345` (Happy Path):** Loads the dashboard cleanly without any interruptions.
- **`54321` (Recoverable Condition):** Loads the dashboard but immediately triggers a blocking "Compliance Notice" interstitial pop-up that the AI must learn to dismiss.
- **`999` (Expected Business Error):** Gracefully stops at the search screen and returns a "Record not found" banner.
- **`500` (Hard Failure / Crash):** Simulates a total mainframe crash (500 Internal Server Error) to break the UI.
- **`777` (Human Handoff / Stuck State):** The "Submit Transaction" button is permanently disabled until a human operator steps in and checks the "Supervisor Override" box.

*(Note: The AI Discovery and Replay documentation will be added here once Phase 4 and Phase 5 are complete).*