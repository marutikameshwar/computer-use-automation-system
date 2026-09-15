import time
import os
import yaml
import logging
from src.schema.models import CapabilityArtifact, ExpectedBusinessOutcome
from src.browser.playwright_wrapper import PlaywrightController
from src.agent.classifier import ClassificationAgent
from src.replay.writer import ArtifactWriter
from src.utils.logger import log_execution
from src.utils.evidence import generate_screenshot_path

logger = logging.getLogger(__name__)

class ReplayEngine:
    def __init__(self, artifact_path: str, capability_dir: str = None):
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"Artifact not found at {artifact_path}")
            
        with open(artifact_path, "r", encoding="utf-8") as f:
            self.artifact = CapabilityArtifact.model_validate_json(f.read())
            
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)["tuning"]
        
        self.capability_dir = capability_dir or os.path.dirname(artifact_path)
        self.controller = PlaywrightController()

    @log_execution
    def run(self, start_url: str, inputs_dict: dict = None) -> dict:
        logger.info("Starting execution of '%s' (version %s)", self.artifact.name, self.artifact.version)
        self.controller.goto(start_url)
        extracted_data = {}
        retry_counts = {}
        
        idx = 0
        while idx < len(self.artifact.steps):
            step = self.artifact.steps[idx]
            logger.info("--- Executing Step %d: %s ---", idx+1, step.action)
            
            loc_strat = step.locator.strategy if step.locator else None
            loc_val = step.locator.value if step.locator else None
            loc_name = step.locator.name if step.locator else None
            
            try:
                if retry_counts.get(idx, 0) >= self.config["max_retries"]:
                    logger.error("Step %d failed %d times. Max retries exceeded.", idx+1, self.config['max_retries'])
                    raise RuntimeError("Max retries exceeded for this step.")
                
                # Runtime parameter injection (prevents mutating the artifact!)
                actual_input_value = step.value
                if actual_input_value and actual_input_value.startswith("{{") and actual_input_value.endswith("}}"):
                    param_key = actual_input_value.strip("{}")
                    if inputs_dict and param_key in inputs_dict:
                        actual_input_value = inputs_dict[param_key]
                
                output = self.controller.execute_action(
                    action=step.action,
                    locator_strategy=loc_strat,
                    locator_value=loc_val,
                    locator_name=loc_name,
                    input_value=actual_input_value
                )
                if step.extract_as and output is not None:
                    extracted_data[step.extract_as] = output
                    logger.info("Extracted '%s': [REDACTED SENSITIVE DATA]", step.extract_as)
                    
                time.sleep(self.config["step_delay_seconds"])
                idx += 1
                
            except Exception as e:
                logger.error("Step %d failed: %s", idx+1, e)
                
                handled = False
                for outcome in self.artifact.expected_outcomes:
                    if self.controller.check_element_exists(
                        strategy=outcome.locator.strategy, 
                        value=outcome.locator.value, 
                        name=outcome.locator.name
                    ):
                        if outcome.severity == "business_outcome":
                            logger.info("Known business outcome: '%s'", outcome.name)
                            logger.info("No human intervention needed. Exiting gracefully.")
                            self._take_screenshot(idx + 1)
                            self.controller.close()
                            return {
                                "status": "business_outcome",
                                "outcome": outcome.name,
                                "step": idx + 1,
                                "outputs": extracted_data
                            }
                        
                        elif outcome.severity == "hard_failure":
                            logger.error("Known hard failure: '%s'", outcome.name)
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
                                logger.info("Operator resolved the issue. Retrying the failed step...")
                                handled = True
                                break
                                
                        elif outcome.severity == "recoverable_condition" and outcome.recovery_action:
                            logger.warning("Known recoverable condition: '%s'", outcome.name)
                            self._take_screenshot(idx + 1)
                            logger.info("Executing autonomous recovery action: %s...", outcome.recovery_action.action)
                            
                            r_strat = outcome.recovery_action.locator.strategy if outcome.recovery_action.locator else None
                            r_val = outcome.recovery_action.locator.value if outcome.recovery_action.locator else None
                            r_name = outcome.recovery_action.locator.name if outcome.recovery_action.locator else None
                            
                            self.controller.execute_action(
                                action=outcome.recovery_action.action,
                                locator_strategy=r_strat,
                                locator_value=r_val,
                                locator_name=r_name,
                                input_value=outcome.recovery_action.value
                            )
                            
                            retry_counts[idx] = retry_counts.get(idx, 0) + 1
                            logger.info("Recovery complete. Retrying Step %d (Attempt %d)...", idx+1, retry_counts[idx])
                            time.sleep(self.config["recovery_delay_seconds"])
                            handled = True
                            break
                
                if handled:
                    continue
                
                logger.error("Checking expected_outcomes... %d outcomes registered. No match.", len(self.artifact.expected_outcomes))
                new_outcome = self._escalate_unknown(idx + 1, str(e))
                if new_outcome:
                    severity, name, rec_action = new_outcome
                    if severity == "business_outcome":
                        logger.info("New business outcome registered: '%s'", name)
                        logger.info("No human intervention needed. Exiting gracefully.")
                        self.controller.close()
                        return {
                            "status": "business_outcome",
                            "outcome": name,
                            "step": idx + 1,
                            "outputs": extracted_data
                        }
                    elif severity == "hard_failure":
                        logger.error("New hard failure registered: '%s'", name)
                        # Create a dummy outcome object to pass to _escalate_known_failure
                        class DummyOutcome:
                            def __init__(self, n): self.name = n
                        aborted = self._escalate_known_failure(idx + 1, DummyOutcome(name))
                        if aborted:
                            self.controller.close()
                            return {
                                "status": "hard_failure_aborted",
                                "outcome": name,
                                "step": idx + 1,
                                "outputs": extracted_data
                            }
                        else:
                            logger.info("Operator resolved the issue. Retrying the failed step...")
                            handled = True
                    elif severity == "recoverable_condition" and rec_action:
                        logger.warning("New recoverable condition registered: '%s'", name)
                        logger.info("Executing autonomous recovery action: %s...", rec_action.get("action"))
                        
                        loc = rec_action.get("locator") or {}
                        r_strat = loc.get("strategy")
                        r_val = loc.get("value")
                        r_name = loc.get("name")
                        
                        self.controller.execute_action(
                            action=rec_action.get("action"),
                            locator_strategy=r_strat,
                            locator_value=r_val,
                            locator_name=r_name,
                            input_value=rec_action.get("value")
                        )
                        
                        retry_counts[idx] = retry_counts.get(idx, 0) + 1
                        logger.info("Recovery complete. Retrying Step %d (Attempt %d)...", idx+1, retry_counts[idx])
                        time.sleep(self.config["recovery_delay_seconds"])
                        handled = True

                if handled:
                    continue

                self.controller.close()
                return {
                    "status": "escalated",
                    "step": idx + 1,
                    "error": str(e),
                    "outputs": extracted_data
                }

        logger.info("Result: SUCCESS")
        if extracted_data:
            logger.info("Outputs: [REDACTED SENSITIVE DATA]")
        self.controller.close()
        return {
            "status": "success",
            "outputs": extracted_data
        }

    @log_execution
    def _escalate_known_failure(self, step_index: int, outcome: ExpectedBusinessOutcome) -> bool:
        self._take_screenshot(step_index)
        
        logger.warning("================ KNOWN HARD FAILURE ================")
        logger.warning("Capability: %s", self.artifact.name)
        logger.warning("Step Index: %d", step_index)
        logger.warning("Error: %s (hard_failure)", outcome.name)
        logger.warning("This is a known system failure. Human intervention required.")
        logger.warning("The browser is still open. Please fix the state of the application.")
        logger.warning("=======================================================")
        choice = input("Press Enter once you have fixed the issue so the agent can resume, or type 'abort' to stop: ").strip()
        
        if choice.lower() == "abort":
            logger.info("Execution aborted by operator.")
            return True
        else:
            action_desc = input("Please describe the manual steps you took in the browser so we can log them for audit: ").strip()
            logger.info("[Operator Log] Human intervention performed: %s", action_desc)
            return False

    @log_execution
    def _escalate_unknown(self, step_index: int, error_msg: str):
        self._take_screenshot(step_index)
        
        logger.warning("================ UNKNOWN STATE DETECTED ================")
        logger.warning("Capability: %s", self.artifact.name)
        logger.warning("Step %d failed: %s", step_index, error_msg)
        
        logger.info("Asking AI to analyze the screen for errors...")
        try:
            tree = self.controller.get_accessibility_tree()
            classifier = ClassificationAgent()
            ai_suggestion = classifier.classify_error(tree)
            
            logger.info("--- AI Suggestion ---")
            logger.info("Name: %s", ai_suggestion.get('name'))
            logger.info("Severity: %s", ai_suggestion.get('severity'))
            logger.info("Recognizer Text: '%s'", ai_suggestion.get('recognizer_text'))
            logger.info("---------------------")
            
            choice = input("\nAccept this AI classification? (y/n): ").strip().lower()
            if choice == 'y':
                error_name = ai_suggestion.get("name")
                severity = ai_suggestion.get("severity")
                recognizer_text = ai_suggestion.get("recognizer_text")
                recovery_action = ai_suggestion.get("recovery_action")
            else:
                raise ValueError("User rejected AI suggestion.")
                
        except Exception as e:
            logger.error("AI classification failed or was rejected: %s", e)
            logger.warning("Falling back to manual input.")
            error_name = input("Enter error name (e.g., record_not_found): ").strip()
            severity_choice = input("Enter severity (1 for business_outcome, 2 for hard_failure, 3 for recoverable_condition): ").strip()
            if severity_choice == "3":
                severity = "recoverable_condition"
            elif severity_choice == "2":
                severity = "hard_failure"
            else:
                severity = "business_outcome"
            recognizer_text = input("Enter the screen text that identifies this error (e.g., 'Record not found'): ").strip()
            recovery_action = None
        
        logger.warning("==========================================================")
        
        if error_name and recognizer_text:
            ArtifactWriter.write_new_version(
                artifact=self.artifact,
                capability_dir=self.capability_dir,
                outcome_name=error_name,
                severity=severity,
                recognizer_text=recognizer_text,
                recovery_action=recovery_action
            )
            return (severity, error_name, recovery_action)
        else:
            logger.error("Insufficient input. No new version created.")
            return None

    def _take_screenshot(self, step_index: int):
        screenshot_path = generate_screenshot_path(f"replay_failure_{self.artifact.name}_step_{step_index}")
        try:
            self.controller.take_screenshot(screenshot_path)
            logger.info("Screenshot saved to %s", screenshot_path)
        except Exception as e:
            logger.error("Failed to capture screenshot: %s", e)
