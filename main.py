import os
import sys
from src.agent.ai_agent import DiscoveryAgent
from src.replay.executor import ReplayEngine
from src.schema.schema import CapabilityArtifact, Locator

def main():
    print("==================================================")
    print("      COMPUTER-USE AUTOMATION ORCHESTRATOR      ")
    print("==================================================\n")
    
    artifact_path = "workflows/mock_bank_tx.json"
    start_url = "http://localhost:5000"
    
    # 1. Check if the blueprint already exists
    if os.path.exists(artifact_path):
        print(f"[*] Blueprint '{artifact_path}' found!")
        print("[*] Bypassing LLM. Routing directly to Deterministic Replay Engine...\n")
        
        # Fast Path: Execute Deterministically
        engine = ReplayEngine(artifact_path)
        engine.run(start_url=start_url)
        
    else:
        print(f"[*] No blueprint found for this task.")
        print("[*] Waking up Discovery Agent (Claude) to learn the path...\n")
        
        # Slow Path: Discover with LLM
        goal = "Search for member 12345, navigate to their dashboard, initiate a savings transaction of 500, reach the confirmation page, extract the full text of the paragraph that starts with 'Successfully processed' into a variable named 'transaction_receipt', and then immediately output an action of wait with a value of DONE."
        agent = DiscoveryAgent()
        
        # The agent.run() method returns the discovered steps
        recorded_steps = agent.run(goal=goal, start_url=start_url)
        
        # We save the blueprint to disk
        artifact = CapabilityArtifact(
            name="Mock Bank Transaction",
            description=goal,
            inputs=["member_id", "amount"],
            steps=recorded_steps,
            success_condition=Locator(strategy="text", value="DONE")
        )
        
        os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        with open(artifact_path, "w") as f:
            f.write(artifact.model_dump_json(indent=2))
        
        print("\n[*] Discovery Complete. Blueprint generated.")
        print("[*] Routing to Deterministic Replay Engine for execution...\n")
        
        # Now execute it deterministically to verify
        engine = ReplayEngine(artifact_path)
        engine.run(start_url=start_url)

if __name__ == "__main__":
    main()
