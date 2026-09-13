import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic
from pydantic import ValidationError

from src.utils.playwright_wrapper import PlaywrightController
from src.schema.schema import Step, CapabilityArtifact, Locator

load_dotenv()

class DiscoveryAgent:
    def __init__(self):
        # Initialize Anthropic Client using the .env key
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.controller = PlaywrightController()

    def run(self, goal: str, start_url: str) -> list[Step]:
        print(f"\n[Discovery Agent] Starting goal: '{goal}'")
        self.controller.goto(start_url)
        
        steps_taken = []
        
        system_prompt = f"""
        You are an advanced banking automation agent. 
        Your overarching goal is: "{goal}"
        
        You will be provided with the Accessibility Tree of the current web page.
        Your job is to decide the single next action to take to progress toward the goal.
        
        You must respond with ONLY valid JSON that strictly matches this Pydantic schema:
        {{
            "action": "click" | "type" | "navigate" | "read_text" | "check" | "wait",
            "locator": {{
                "strategy": "role" | "text" | "label" | "placeholder" | "exact_text",
                "value": "string",
                "name": "string (optional, usually needed if strategy is role)"
            }},
            "value": "string (optional, use this for the text to type)",
            "extract_as": "string (optional, variable name to save read text into)"
        }}
        
        Example valid JSON for clicking a button:
        {{
          "action": "click",
          "locator": {{
            "strategy": "role",
            "value": "button",
            "name": "Submit"
          }}
        }}

        Example typing into a nameless amount field:
        {{
          "action": "type",
          "locator": {{
            "strategy": "role",
            "value": "spinbutton"
          }},
          "value": "500"
        }}
        
        If you have completely achieved the goal, output an action of "wait" and a value of "DONE".
        Do not include any markdown formatting, conversational text, or explanations. Only the raw JSON object.
        """

        # The loop (Observe -> Decide -> Act)
        max_steps = 10
        for i in range(max_steps):
            print(f"\n--- Step {i+1} ---")
            
            # 1. OBSERVE
            tree = self.controller.get_accessibility_tree()
            
            prompt = f"Current Accessibility Tree:\n{tree}\n\nWhat is the next action?"
            
            # 2. DECIDE
            print("[Discovery Agent] Asking Claude for the next move...")
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the text block (ignoring any ThinkingBlocks if extended reasoning is enabled)
            json_str = ""
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    json_str = block.text.strip()
                    break
            
            # Fallback if somehow it's not a block object
            if not json_str and hasattr(response.content[0], "text"):
                json_str = response.content[0].text.strip()
            
            # Basic cleanup in case Claude added markdown
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            print(f"[Discovery Agent] Claude returned:\n{json_str}")
            
            # --- SELF-HEALING BLOCK ---
            try:
                # We force Pydantic to validate Claude's JSON
                step = Step.model_validate_json(json_str)
            except ValidationError as e:
                # If Claude hallucinates a bad field, we catch the error!
                print(f"[ERROR] Pydantic rejected Claude's JSON: {e}")
                print("In a fully self-healing loop, we would feed this error right back to Claude to fix. Stopping here for safety.")
                break
            # --------------------------

            # Check for completion condition
            if step.action == "wait" and step.value == "DONE":
                print("\n[Discovery Agent] Goal successfully achieved!")
                break
                
            # 3. ACT
            steps_taken.append(step)
            
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
                print(f"[Discovery Agent] Extracted data saved to '{step.extract_as}': {extracted_data}")

        self.controller.close()
        
        print(f"\n[Discovery Agent] Run finished. Recorded {len(steps_taken)} steps.")
        return steps_taken

# A quick block to run it directly from the terminal for testing
if __name__ == "__main__":
    agent = DiscoveryAgent()
    # The Goal: Use the Happy Path (12345)
    test_goal = "Search for member 12345, navigate to their dashboard, initiate a savings transaction of 500, and reach the confirmation page."
    recorded_steps = agent.run(goal=test_goal, start_url="http://localhost:5000")
    
    print("\n--- FINAL RECORDED STEPS FOR ARTIFACT ---")
    for s in recorded_steps:
        # Redact the output log for safety
        dump_s = s.model_copy()
        if dump_s.action == "type":
            dump_s.value = "[REDACTED]"
        print(dump_s.model_dump_json(indent=2))
        
    # Phase 4 Completion: Actually save the artifact to disk!
    from src.schema.models import CapabilityArtifact, Locator
    
    artifact = CapabilityArtifact(
        name="Mock Bank Transaction",
        description=test_goal,
        inputs=["member_id", "amount"],
        steps=recorded_steps,
        success_condition=Locator(strategy="text", value="DONE")
    )
    
    with open("artifact.json", "w") as f:
        f.write(artifact.model_dump_json(indent=2))
    
    print("\n[Discovery Agent] Successfully saved artifact.json to disk! Ready for Phase 5.")
