import pytest
import json
from src.agent.discovery import DiscoveryAgent
from src.schema.models import Step

@pytest.fixture
def mock_anthropic_client(mocker):
    return mocker.patch("src.agent.discovery.Anthropic")

@pytest.mark.unit
def test_discovery_agent_init(mock_anthropic_client):
    agent = DiscoveryAgent()
    assert agent.client is not None
    assert agent.config is not None
    mock_anthropic_client.assert_called_once()

@pytest.mark.unit
def test_run_success(mock_anthropic_client, mock_playwright):
    agent = DiscoveryAgent()
    
    # Setup the mock Anthropic response
    mock_message = mock_anthropic_client.return_value.messages.create.return_value
    mock_message.content = [
        type('obj', (object,), {'text': '{"action": "navigate", "value": "http://localhost", "reasoning": "Go to page"}'})()
    ]
    
    # We want it to finish in 1 step, so the second call should return wait with value DONE
    mock_message_2 = type('obj', (object,), {'content': [type('obj', (object,), {'text': '{"action": "wait", "value": "DONE", "reasoning": "Done"}'})()]})
    mock_anthropic_client.return_value.messages.create.side_effect = [
        mock_message,
        mock_message_2
    ]
    
    # Setup Playwright mock
    mock_playwright.get_accessibility_tree.return_value = "mock tree"
    
    # Speed up by lowering max_steps to 2
    agent.config["max_discovery_steps"] = 2
    
    steps = agent.run("Do something", "http://localhost")
    
    assert len(steps) == 2
    assert steps[0].action == "navigate"
    assert steps[0].value == "http://localhost"

@pytest.mark.unit
def test_run_invalid_json(mock_anthropic_client, mock_playwright):
    agent = DiscoveryAgent()
    
    # Return bad JSON first, then wait to break out
    mock_message_1 = type('obj', (object,), {'content': [type('obj', (object,), {'text': 'BAD JSON'})()]})
    mock_message_2 = type('obj', (object,), {'content': [type('obj', (object,), {'text': '{"action": "wait", "value": "DONE"}'})()]})
    
    mock_anthropic_client.return_value.messages.create.side_effect = [
        mock_message_1,
        mock_message_2
    ]
    
    agent.config["max_discovery_steps"] = 1
    
    steps = agent.run("Goal", "http://localhost")
    # Because of bad JSON, the step is skipped, and it returns None
    assert steps is None

@pytest.mark.unit
def test_run_max_steps_exceeded(mock_anthropic_client, mock_playwright):
    agent = DiscoveryAgent()
    
    # Always return a normal action
    mock_message = type('obj', (object,), {'content': [type('obj', (object,), {'text': '{"action": "wait", "value": "NOT_DONE"}'})()]})
    mock_anthropic_client.return_value.messages.create.return_value = mock_message
    
    # The config limits it to 10 steps usually (or whatever is in config)
    # We can patch the config to make the test faster
    agent.config["max_discovery_steps"] = 3
    
    steps = agent.run("Goal", "http://localhost")

    # Should stop at 3 steps and return None
    assert steps is None
