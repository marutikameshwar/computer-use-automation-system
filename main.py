import os
import sys
import json
import glob
from src.agent.ai_agent import DiscoveryAgent
from src.replay.executor import ReplayEngine
from src.schema.schema import CapabilityArtifact, Locator


# Configuration
CAPABILITY_NAME = "mock_bank_tx"
CAPABILITY_DIR = os.path.join("workflows", CAPABILITY_NAME)
START_URL = "http://localhost:5000"
DISCOVERY_GOAL = (
    "Search for member 12345, navigate to their dashboard, "
    "initiate a savings transaction of 500, reach the confirmation page, "
    "extract the full text of the paragraph that starts with 'Successfully processed' "
    "into a variable named 'transaction_receipt', and then immediately output an action "
    "of wait with a value of DONE."
)


def resolve_version():
    """
    Version Loader: Read the pointer file to find the current approved version.
    Returns the path to the versioned JSON file, or None if no capability exists.
    """
    pointer_path = os.path.join(CAPABILITY_DIR, "current.txt")
    
    if not os.path.exists(pointer_path):
        return None
    
    with open(pointer_path, "r") as f:
        current_version = f.read().strip()
    
    artifact_path = os.path.join(CAPABILITY_DIR, f"v{current_version}.json")
    
    if not os.path.exists(artifact_path):
        print(f"[Orchestrator] ERROR: Pointer says v{current_version} but {artifact_path} not found.")
        return None
    
    return artifact_path


def run_discovery():
    """
    Discovery path: Use the LLM to learn a new capability.
    Creates v1.json and sets the pointer.
    """
    print(f"[Orchestrator] No existing capability found. Starting Discovery...\n")
    
    # Run the Discovery Agent (Claude)
    agent = DiscoveryAgent()
    recorded_steps = agent.run(goal=DISCOVERY_GOAL, start_url=START_URL)
    
    if not recorded_steps:
        print("\n[Orchestrator] Discovery failed: No steps recorded.")
        return
    
    # Build the v1 artifact
    artifact = CapabilityArtifact(
        version=1,
        name="Mock Bank Transaction",
        description=DISCOVERY_GOAL,
        inputs=["member_id", "amount"],
        steps=recorded_steps,
        success_condition=Locator(strategy="text", value="Successfully processed")
    )
    
    # Create the capability directory and save v1
    os.makedirs(CAPABILITY_DIR, exist_ok=True)
    
    v1_path = os.path.join(CAPABILITY_DIR, "v1.json")
    with open(v1_path, "w") as f:
        f.write(artifact.model_dump_json(indent=2))
    
    # Set the pointer
    pointer_path = os.path.join(CAPABILITY_DIR, "current.txt")
    with open(pointer_path, "w") as f:
        f.write("1")
    
    print(f"\n[Writer] Saved: {v1_path} (version 1)")
    print(f"[Writer] Pointer set: current.txt → 1")
    print(f"[Orchestrator] Discovery complete. Ready for replay.")


def run_replay(member_id: str):
    """
    Replay path: Execute the capability deterministically with the given member_id.
    """
    artifact_path = resolve_version()
    
    version = os.path.basename(artifact_path).replace("v", "").replace(".json", "")
    print(f"[Orchestrator] Loading capability '{CAPABILITY_NAME}' (version {version})")
    print(f"[Orchestrator] Bypassing LLM. Routing to Deterministic Replay Engine...\n")
    
    # Load the engine
    engine = ReplayEngine(artifact_path, capability_dir=CAPABILITY_DIR)
    
    # Parameterize: replace the training value '12345' with the dynamic member_id
    for step in engine.artifact.steps:
        if step.action == "type" and step.value == "12345":
            step.value = member_id
            break
    
    # Execute
    result = engine.run(start_url=START_URL)
    
    # Print the structured result
    print(f"\n{'='*50}")
    print(f"STRUCTURED RESULT:")
    print(json.dumps(result, indent=2))
    print(f"{'='*50}")


def main():
    print("==================================================")
    print("      COMPUTER-USE AUTOMATION ORCHESTRATOR      ")
    print("==================================================\n")
    
    # Check if the capability already exists
    artifact_path = resolve_version()
    
    if artifact_path is None:
        # No blueprint → Discovery
        run_discovery()
    else:
        # Blueprint exists → Replay
        member_id = input("Enter Member ID (e.g. 12345, 999, 500): ").strip()
        if not member_id:
            member_id = "12345"
        run_replay(member_id)


if __name__ == "__main__":
    main()
