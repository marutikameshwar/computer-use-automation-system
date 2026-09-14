class PromptManager:
    @staticmethod
    def get_discovery_system_prompt(goal: str, allowed_actions: list) -> str:
        allowed_actions_str = ' | '.join([f'"{a}"' for a in allowed_actions])
        return f"""
        You are an advanced banking automation agent. 
        Your overarching goal is: "{goal}"
        
        You will be provided with the Accessibility Tree of the current web page.
        Your job is to decide the single next action to take to progress toward the goal.
        
        You must respond with ONLY valid JSON that strictly matches this Pydantic schema:
        {{
            "thought": "string (brief reasoning for why you are taking this action)",
            "action": "{allowed_actions_str}",
            "locator": {{
                "strategy": "role" | "text" | "label" | "placeholder",
                "value": "string",
                "name": "string (optional, usually needed if strategy is role)"
            }},
            "value": "string (optional, use this for the text to type)",
            "extract_as": "string (optional, variable name to save read text into)"
        }}
        
        Example valid JSON for clicking a button:
        {{
          "thought": "The 'Submit' button is now visible, I need to click it to proceed.",
          "action": "click",
          "locator": {{
            "strategy": "role",
            "value": "button",
            "name": "Submit"
          }}
        }}

        Example typing into a nameless amount field:
        {{
          "thought": "I need to enter the transfer amount into the spinbutton field.",
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

    @staticmethod
    def get_discovery_user_prompt(accessibility_tree: str, history: str) -> str:
        return f"Current Accessibility Tree:\n{accessibility_tree}\n\nSteps you have already completed:\n{history}\n\nWhat is the single next action? If you have already extracted the data requested in the goal, your next action MUST be wait with value DONE."

    @staticmethod
    def get_classification_prompt(accessibility_tree: str) -> str:
        return f"""
        The automated agent was trying to complete a task, but an error occurred on the page.
        Here is the accessibility tree of the current page:
        {accessibility_tree}
        
        Identify the prominent error message, state change, or modal popup on the screen.
        Provide a short machine-readable name for it (e.g., 'record_not_found', 'promotional_popup').
        
        Determine its severity from these 3 options:
        1. 'business_outcome' (a legitimate application response like 'no results')
        2. 'hard_failure' (a system crash like 500 internal server error)
        3. 'recoverable_condition' (an unexpected block, like a newsletter popup, that can be dismissed to continue).
        
        Provide the exact text on the screen that we can use as a locator to recognize this state in the future.
        CRITICAL: Ensure the recognizer text does NOT contain any emojis or special graphical symbols. Only output standard alphanumeric text (e.g. use "Mandatory Notice" instead of "[!] Mandatory Notice").
        
        If it is a 'recoverable_condition', also provide a 'recovery_action' (a single step to dismiss the block).
        
        Return ONLY a JSON object in this format:
        {{
            "name": "string",
            "severity": "business_outcome" | "hard_failure" | "recoverable_condition",
            "recognizer_text": "string without emojis",
            "recovery_action": {{
                "action": "click",
                "locator": {{
                    "strategy": "role" | "text" | "label",
                    "value": "string",
                    "name": "string (optional)"
                }}
            }} // ONLY include this field if severity is 'recoverable_condition'
        }}
        """
