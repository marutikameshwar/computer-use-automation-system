import os
import json
import yaml
import logging
from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import ValidationError

from src.browser.playwright_wrapper import PlaywrightController
from src.schema.models import Step
from src.prompts.prompts import PromptManager
from src.utils.logger import log_execution
from src.utils.evidence import generate_screenshot_path

logger = logging.getLogger(__name__)
load_dotenv()

class DiscoveryAgent:
    def __init__(self):
        with open("config.yaml", "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f)
            self.config = full_config["ai_settings"]
            self.safety_config = full_config["safety"]
            
        # Initialize Anthropic Client using the .env key
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.controller = PlaywrightController()

    @log_execution
    def run(self, goal: str, start_url: str) -> list[Step]:
        logger.info("Starting goal: '%s'", goal)
        self.controller.goto(start_url)
        
        steps_taken = []
        system_prompt = PromptManager.get_discovery_system_prompt(goal, self.safety_config['allowed_actions'])

        max_steps = self.config["max_discovery_steps"]
        try:
            for i in range(max_steps):
                logger.info("--- Step %d ---", i+1)
            
                tree = self.controller.get_accessibility_tree()
            
                history = "None yet." if not steps_taken else json.dumps(
                    [s.model_dump(exclude_none=True) for s in steps_taken], indent=2
                )
            
                prompt = PromptManager.get_discovery_user_prompt(tree, history)
            
                logger.info("Asking Claude for the next move...")
                try:
                    response = self.client.messages.create(
                        model=self.config["model_name"],
                        max_tokens=self.config["max_tokens"],
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": prompt}
                        ]
                    )
                except Exception as api_err:
                    logger.exception("Anthropic API failed")
                    logger.error("Run aborted due to API failure.")
                    return None
            
                json_str = ""
                for block in response.content:
                    if getattr(block, "type", "") == "text":
                        json_str = block.text.strip()
                        break
            
                if not json_str and hasattr(response.content[0], "text"):
                    json_str = response.content[0].text.strip()
            
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()

                try:
                    log_data = json.loads(json_str)
                    if log_data.get("action") == "type" and "value" in log_data:
                        log_data["value"] = "[REDACTED]"
                    logger.info("Claude returned:\n%s", json.dumps(log_data, indent=2))
                except json.JSONDecodeError:
                    logger.warning("Claude returned raw output (redacted for safety).")
            
                try:
                    step = Step.model_validate_json(json_str)
                except ValidationError as e:
                    logger.exception("Pydantic rejected Claude's JSON")
                    logger.warning("In a fully self-healing loop, we would feed this error right back to Claude to fix. Stopping here for safety.")
                    break

                steps_taken.append(step)

                if step.action == "wait" and step.value == "DONE":
                    logger.info("Goal successfully achieved!")
                    break
            
                loc_strat = step.locator.strategy if step.locator else None
                loc_val = step.locator.value if step.locator else None
                loc_name = step.locator.name if step.locator else None
            
                extracted_data = self.controller.execute_action(
                    action=step.action,
                    locator_strategy=loc_strat,
                    locator_value=loc_val,
                    locator_name=loc_name,
                    input_value=step.value
                )
            
                if extracted_data and step.extract_as:
                    logger.info("Extracted data saved to '%s': [REDACTED SENSITIVE DATA]", step.extract_as)

        except Exception as e:
            logger.exception("Unexpected system failure during discovery")
            try:
                ss_path = generate_screenshot_path("discovery_crash")
                self.controller.take_screenshot(ss_path)
                logger.info("Screenshot saved to: %s", ss_path)
            except Exception as ss_err:
                logger.error("Failed to take screenshot: %s", ss_err)
            self.controller.close()
            return None

        self.controller.close()
        
        if not steps_taken or not (steps_taken[-1].action == "wait" and steps_taken[-1].value == "DONE"):
            logger.error("Goal was NOT successfully achieved within %d steps.", max_steps)
            try:
                ss_path = generate_screenshot_path(f"discovery_timeout_step_{len(steps_taken)}")
                self.controller.take_screenshot(ss_path)
                logger.info("Screenshot saved to: %s", ss_path)
            except Exception as ss_err:
                logger.error("Failed to take screenshot: %s", ss_err)
            return None
            
        logger.info("Run finished successfully. Recorded %d steps.", len(steps_taken))
        return steps_taken
