import time
import json
import os
import copy
from datetime import datetime
from src.schema.schema import CapabilityArtifact, ExpectedBusinessOutcome, Locator
from src.utils.playwright_wrapper import PlaywrightController
from src.agent.ai_agent import ClassificationAgent


class ReplayEngine:
    def __init__(self, artifact_path: str, capability_dir: str = None):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Artifact not found at {artifact_path}")
            
        with open(artifact_path, "r") as f:
            self.artifact = CapabilityArtifact.model_validate_json(f.read())
        
        # The directory where versioned files live (e.g., workflows/mock_bank_tx/)
        self.capability_dir = capability_dir or os.path.dirname(artifact_path)
        self.controller = PlaywrightController()

    def run(self, start_url: str) -> dict:
        """
        Execute the artifact deterministically.
        Returns a structured result dict with status and data.
        """
        print(f"\n[Replay Engine] Starting execution of '{self.artifact.name}' (version {self.artifact.version})")
        self.controller.goto(start_url)
        extracted_data = {}
        
        idx = 0
        while idx < len(self.artifact.steps):
            step = self.artifact.steps[idx]
            print(f"--- Executing Step {idx+1}: {step.action} ---")
            
            loc_strat = step.locator.strategy if step.locator else None
            loc_val = step.locator.value if step.locator else None
            loc_name = step.locator.name if step.locator else None
            
            try:
                output = self.controller.execute_action(
                    action=step.action,
                    locator_strategy=loc_strat,
                    locator_value=loc_val,
                    locator_name=loc_name,
                    input_value=step.value
                )
                if step.extract_as and output is not None:
                    extracted_data[step.extract_as] = output
                    print(f"[Replay Engine] Extracted '{step.extract_as}': {output}")
                    
                # Small sleep to let the page react
                time.sleep(0.5)
                
                # Advance to next step if successful
                idx += 1
                
            except Exception as e:
                print(f"\n[ERROR] Step {idx+1} failed: {e}")
                
                # --- SEVERITY-AWARE ERROR HANDLING ---
                
                # 1. Check all known expected outcomes
                handled = False
                for outcome in self.artifact.expected_outcomes:
                    if self.controller.check_element_exists(
                        strategy=outcome.locator.strategy, 
                        value=outcome.locator.value, 
                        name=outcome.locator.name
                    ):
                        if outcome.severity == "business_outcome":
                            # AUTOMATIC: Return gracefully, no human needed
                            print(f"\n[Replay Engine] Known business outcome: '{outcome.name}'")
                            print(f"[Replay Engine] No human intervention needed. Exiting gracefully.")
                            self.controller.close()
                            return {
                                "status": "business_outcome",
                                "outcome": outcome.name,
                                "step": idx + 1,
                                "outputs": extracted_data
                            }
                        
                        elif outcome.severity == "hard_failure":
                            # ALWAYS ESCALATE: System is broken, human must fix
                            print(f"\n[Replay Engine] Known hard failure: '{outcome.name}'")
                            aborted = self._escalate_known_failure(idx + 1, outcome)
                            if aborted:
                                self.controller.close()
                                return {
                                    "status": "hard_failure_aborted",
                                    "outcome": outcome.name,
                                    "step": idx + 1,
                                    "outputs": extracted_data
                                }
                            else:
                                # The human fixed it and pressed Enter! We want to resume.
                                print("[Replay Engine] Operator resolved the issue. Retrying the failed step...")
                                handled = True
                                break # break the outcome checking loop
                
                if handled:
                    continue # continue loops back to the while condition without incrementing idx, so it retries!
                
                # 2. Nothing matched → Truly unknown state → Classify + Write new version
                print(f"\n[Replay Engine] Checking expected_outcomes... {len(self.artifact.expected_outcomes)} outcomes registered. No match.")
                self._escalate_unknown(idx + 1, str(e))
                self.controller.close()
                return {
                    "status": "escalated",
                    "step": idx + 1,
                    "error": str(e),
                    "outputs": extracted_data
                }

        # All steps completed successfully
        print(f"\n[Replay Engine] Result: SUCCESS")
        if extracted_data:
            print(f"[Replay Engine] Outputs: {json.dumps(extracted_data, indent=2)}")
        self.controller.close()
        return {
            "status": "success",
            "outputs": extracted_data
        }

    def _escalate_known_failure(self, step_index: int, outcome: ExpectedBusinessOutcome) -> bool:
        """
        Called when a KNOWN hard failure is detected.
        Returns True if the operator aborted, False if they want to resume.
        """
        self._take_screenshot(step_index)
        
        print(f"\n================ KNOWN HARD FAILURE ================")
        print(f"Error: {outcome.name} (hard_failure)")
        print(f"This is a known system failure. Human intervention required.")
        print(f"The browser is still open. Please fix the state of the application.")
        print(f"=======================================================")
        choice = input("Press Enter once you have fixed the issue so the agent can resume, or type 'abort' to stop: ").strip()
        
        if choice.lower() == "abort":
            print("[Replay Engine] Execution aborted by operator.")
            return True
        else:
            return False

    def _escalate_unknown(self, step_index: int, error_msg: str):
        """
        Called when an UNKNOWN state is encountered (no expected_outcome matched).
        The human classifies the error, and the Writer creates a new immutable version.
        """
        self._take_screenshot(step_index)
        
        print(f"\n================ UNKNOWN STATE DETECTED ================")
        print(f"Step {step_index} failed: {error_msg}")
        
        print("\n[Replay Engine] Asking AI to analyze the screen for errors...")
        try:
            tree = self.controller.get_accessibility_tree()
            classifier = ClassificationAgent()
            ai_suggestion = classifier.classify_error(tree)
            
            print("\n--- AI Suggestion ---")
            print(f"Name: {ai_suggestion.get('name')}")
            print(f"Severity: {ai_suggestion.get('severity')}")
            print(f"Recognizer Text: '{ai_suggestion.get('recognizer_text')}'")
            print("---------------------")
            
            choice = input("\nAccept this AI classification? (y/n): ").strip().lower()
            if choice == 'y':
                error_name = ai_suggestion.get("name")
                severity = ai_suggestion.get("severity")
                recognizer_text = ai_suggestion.get("recognizer_text")
            else:
                raise ValueError("User rejected AI suggestion.")
                
        except Exception as e:
            print(f"\n[Replay Engine] AI classification failed or was rejected: {e}")
            print(f"Falling back to manual input.")
            error_name = input("Enter error name (e.g., record_not_found): ").strip()
            severity_choice = input("Enter severity (1 for business_outcome, 2 for hard_failure): ").strip()
            severity = "hard_failure" if severity_choice == "2" else "business_outcome"
            recognizer_text = input("Enter the screen text that identifies this error (e.g., 'Record not found'): ").strip()
        
        print(f"==========================================================")
        
        if error_name and recognizer_text:
            self._write_new_version(error_name, severity, recognizer_text)
        else:
            print("[Replay Engine] Insufficient input. No new version created.")

    def _write_new_version(self, outcome_name: str, severity: str, recognizer_text: str):
        """
        The Writer — the ONLY component with write access to the artifact registry.
        Deep-copies the current version, applies the approved delta, and saves as a new immutable file.
        """
        new_version = self.artifact.version + 1
        intervention_id = f"INT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Deep-copy the current artifact
        artifact_data = json.loads(self.artifact.model_dump_json())
        
        # Apply the narrow delta: add one ExpectedBusinessOutcome
        new_outcome = ExpectedBusinessOutcome(
            name=outcome_name,
            severity=severity,
            locator=Locator(strategy="text", value=recognizer_text)
        )
        artifact_data["expected_outcomes"].append(new_outcome.model_dump())
        
        # Update version metadata
        artifact_data["version"] = new_version
        artifact_data["derived_from"] = self.artifact.version
        artifact_data["intervention_id"] = intervention_id
        
        # Validate the merged artifact (Gate 1: Schema revalidation)
        try:
            validated = CapabilityArtifact.model_validate(artifact_data)
        except Exception as e:
            print(f"[Writer] ERROR: Schema validation failed. No version written: {e}")
            return
        
        # Write the new immutable file
        new_path = os.path.join(self.capability_dir, f"v{new_version}.json")
        with open(new_path, "w") as f:
            f.write(validated.model_dump_json(indent=2))
        
        # Update the pointer
        pointer_path = os.path.join(self.capability_dir, "current.txt")
        with open(pointer_path, "w") as f:
            f.write(str(new_version))
        
        print(f"\n[Writer] Deep-copying v{self.artifact.version} → v{new_version}")
        print(f"[Writer] Adding outcome: {outcome_name} ({severity})")
        print(f"[Writer] Saved: {new_path} (derived_from: {self.artifact.version}, intervention: {intervention_id})")
        print(f"[Writer] Pointer updated: current.txt → {new_version}")

    def _take_screenshot(self, step_index: int):
        """Take a screenshot for evidence/debugging."""
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        screenshot_path = f"logs/escalation_step_{step_index}.png"
        try:
            self.controller.take_screenshot(screenshot_path)
            print(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            print(f"Could not take screenshot: {e}")
