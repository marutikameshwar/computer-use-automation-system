import pytest
from src.prompts.prompts import PromptManager

@pytest.mark.unit
def test_discovery_system_prompt():
    prompt = PromptManager.get_discovery_system_prompt("Navigate and login", ["click", "type"])
    assert "Navigate and login" in prompt
    assert "click" in prompt
    assert "type" in prompt
    assert "advanced banking automation agent" in prompt

@pytest.mark.unit
def test_discovery_user_prompt():
    prompt = PromptManager.get_discovery_user_prompt("<button>Submit</button>", "None yet.")
    assert "<button>Submit</button>" in prompt
    assert "None yet." in prompt

@pytest.mark.unit
def test_classification_prompt():
    prompt = PromptManager.get_classification_prompt("<h1>Error 404</h1>")
    assert "<h1>Error 404</h1>" in prompt
    assert "accessibility tree" in prompt
