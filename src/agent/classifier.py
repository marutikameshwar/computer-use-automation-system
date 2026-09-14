import os
import json
import yaml
import logging
from dotenv import load_dotenv
from anthropic import Anthropic

from src.prompts.prompts import PromptManager
from src.utils.logger import log_execution

logger = logging.getLogger(__name__)
load_dotenv()

class ClassificationAgent:
    def __init__(self):
        with open("config.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)["ai_settings"]
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    @log_execution
    def classify_error(self, accessibility_tree: str) -> dict:
        """
        Analyzes the screen to classify an unknown error.
        Returns a dictionary with 'name', 'severity', and 'recognizer_text'.
        """
        prompt = PromptManager.get_classification_prompt(accessibility_tree)
        response = self.client.messages.create(
            model=self.config["model_name"],
            max_tokens=self.config["max_tokens"],
            messages=[{"role": "user", "content": prompt}]
        )
        
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
            
        return json.loads(json_str)
