import os
import json
import logging
from datetime import datetime
from src.schema.models import CapabilityArtifact, ExpectedBusinessOutcome, Locator
from src.utils.logger import log_execution

logger = logging.getLogger(__name__)

class ArtifactWriter:
    @staticmethod
    @log_execution
    def write_new_version(artifact: CapabilityArtifact, capability_dir: str, outcome_name: str, severity: str, recognizer_text: str, recovery_action: dict = None):
        new_version = artifact.version + 1
        intervention_id = f"INT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        artifact_data = json.loads(artifact.model_dump_json())
        
        new_outcome = ExpectedBusinessOutcome(
            name=outcome_name,
            severity=severity,
            locator=Locator(strategy="text", value=recognizer_text),
            recovery_action=recovery_action
        )
        artifact_data["expected_outcomes"].append(new_outcome.model_dump())
        
        artifact_data["version"] = new_version
        artifact_data["derived_from"] = artifact.version
        artifact_data["intervention_id"] = intervention_id
        
        try:
            validated = CapabilityArtifact.model_validate(artifact_data)
        except Exception as e:
            logger.error("Schema validation failed. No version written: %s", e)
            return
        
        new_path = os.path.join(capability_dir, f"v{new_version}.json")
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(validated.model_dump_json(indent=2))
        
        pointer_path = os.path.join(capability_dir, "current.txt")
        with open(pointer_path, "w", encoding="utf-8") as f:
            f.write(str(new_version))
        
        logger.info("Deep-copying v%d -> v%d", artifact.version, new_version)
        logger.info("Adding outcome: %s (%s)", outcome_name, severity)
        logger.info("Saved: %s (derived_from: %d, intervention: %s)", new_path, artifact.version, intervention_id)
        logger.info("Pointer updated: current.txt -> %d", new_version)
