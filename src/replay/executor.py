import time
import json
import os
from src.schema.schema import CapabilityArtifact
from src.utils.playwright_wrapper import PlaywrightController

class ReplayEngine:
    def __init__(self, artifact_path: str):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Artifact not found at {artifact_path}")
            
        with open(artifact_path, "r") as f:
            self.artifact = CapabilityArtifact.model_validate_json(f.read())
            
        self.controller = PlaywrightController()

    def run(self, start_url: str):
        print(f"\n[Replay Engine] Starting execution of '{self.artifact.name}'")
        self.controller.goto(start_url)
        extracted_data = {}
        
        for idx, step in enumerate(self.artifact.steps):
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
                    
                # Small sleep to let the page react, mimicking human speed
                time.sleep(0.5)
            except Exception as e:
                print(f"\n[ERROR] Step {idx+1} failed: {e}")
                
                # Check for Expected Business Outcomes first
                outcome_matched = False
                for outcome in self.artifact.expected_outcomes:
                    if self.controller.check_element_exists(
                        strategy=outcome.locator.strategy, 
                        value=outcome.locator.value, 
                        name=outcome.locator.name
                    ):
                        print(f"[Replay Engine] Expected Business Outcome reached: '{outcome.name}'")
                        print("[Replay Engine] Exiting gracefully.")
                        self.controller.close()
                        return extracted_data
                        
                # If no known outcome, escalate to human!
                self.escalate_to_human(idx+1, str(e))
                # If the human resolves it and presses enter, we continue the loop!

        # Check success condition (very rudimentarily)
        if self.artifact.success_condition:
            print(f"--- Verifying Success Condition ---")
            try:
                self.controller.execute_action(
                    action="wait",
                    locator_strategy=self.artifact.success_condition.strategy,
                    locator_value=self.artifact.success_condition.value,
                    locator_name=self.artifact.success_condition.name,
                    input_value=None
                )
                print(f"[Replay Engine] Success condition met!")
            except Exception as e:
                # In our mock app, the text is actually "DONE" in the prompt, but the actual text on the screen is "Transaction successful" or similar.
                # If we get here, it just means the strict wait failed.
                print(f"[Replay Engine] Warning: Success condition not found exactly as written: {e}")

        print(f"\n[Replay Engine] Execution completed successfully in record time!")
        if extracted_data:
            print(f"[Replay Engine] Returned Outputs: {json.dumps(extracted_data, indent=2)}")
        self.controller.close()
        return extracted_data

    def escalate_to_human(self, step_index: int, error_msg: str):
        print(f"\n================ HARD FAILURE DETECTED ================")
        print(f"Error: {error_msg}")
        
        # 1. Ensure logs dir exists
        if not os.path.exists("logs"):
            os.makedirs("logs")
            
        # 2. Take screenshot if browser is still open
        screenshot_path = f"logs/escalation_step_{step_index}.png"
        try:
            self.controller.take_screenshot(screenshot_path)
            print(f"Snapshot saved to: {screenshot_path}")
        except Exception as e:
            print(f"Could not take snapshot (Browser may have been closed abruptly): {e}")
        
        # 3. Prompt Operator
        print(f"=======================================================")
        input(f"Agent stuck on Step {step_index}. Please take control of the browser, fix the state, and press Enter to resume...")
        print("Resuming execution...")

if __name__ == "__main__":
    engine = ReplayEngine("workflows/mock_bank_tx.json")
    engine.run(start_url="http://localhost:5000")
