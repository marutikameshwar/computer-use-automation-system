import os
import json
import logging
from src.agent.discovery import DiscoveryAgent
from src.replay.engine import ReplayEngine
from src.schema.models import CapabilityArtifact, Locator

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, capability_name: str):
        self.capability_name = capability_name
        self.capability_dir = os.path.join("src", "workflows", capability_name)

    def resolve_version(self):
        pointer_path = os.path.join(self.capability_dir, "current.txt")
        
        if not os.path.exists(pointer_path):
            return None
        
        with open(pointer_path, "r", encoding="utf-8") as f:
            current_version = f.read().strip()
        
        artifact_path = os.path.join(self.capability_dir, f"v{current_version}.json")
        
        if not os.path.exists(artifact_path):
            logger.error("Pointer says v%s but %s not found.", current_version, artifact_path)
            return None
        
        return artifact_path

    def run_discovery(self, goal: str, start_url: str):
        logger.info("No existing capability found. Starting Discovery...")
        logger.info("Goal: %s", goal)
        logger.info("URL: %s", start_url)
        
        agent = DiscoveryAgent()
        recorded_steps = agent.run(goal=goal, start_url=start_url)
        
        if not recorded_steps:
            logger.error("Discovery failed: No steps recorded.")
            return
        
        input_idx = 0
        inputs_list = ["member_id", "amount"]
        for step in recorded_steps:
            if step.action == "type":
                param_name = inputs_list[input_idx] if input_idx < len(inputs_list) else "parameter"
                step.value = f"{{{{{param_name}}}}}"
                input_idx += 1

        artifact = CapabilityArtifact(
            version=1,
            name="Mock Bank Transaction",
            description=goal,
            inputs=inputs_list,
            steps=recorded_steps,
            success_condition=Locator(strategy="text", value="Successfully processed")
        )
        
        os.makedirs(self.capability_dir, exist_ok=True)
        
        v1_path = os.path.join(self.capability_dir, "v1.json")
        with open(v1_path, "w", encoding="utf-8") as f:
            f.write(artifact.model_dump_json(indent=2))
        
        pointer_path = os.path.join(self.capability_dir, "current.txt")
        with open(pointer_path, "w", encoding="utf-8") as f:
            f.write("1")
        
        logger.info("Saved: %s (version 1)", v1_path)
        logger.info("Pointer set: current.txt -> 1")
        logger.info("Discovery complete. Ready for replay.")

    def run_replay(self, member_id: str, start_url: str, artifact_path: str):
        version = os.path.basename(artifact_path).replace("v", "").replace(".json", "")
        logger.info("Loading capability '%s' (version %s)", self.capability_name, version)
        logger.info("Bypassing LLM. Routing to Deterministic Replay Engine...")
        
        engine = ReplayEngine(artifact_path, capability_dir=self.capability_dir)
        
        inputs_dict = {
            "member_id": member_id,
            "amount": "500"
        }
        
        result = engine.run(start_url=start_url, inputs_dict=inputs_dict)
        logger.info("STRUCTURED RESULT:\n%s", json.dumps(result, indent=2))
