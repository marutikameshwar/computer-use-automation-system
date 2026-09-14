import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_playwright(mocker):
    """Mocks the PlaywrightController completely to prevent browser popups during tests."""
    mock_class = mocker.patch("src.browser.playwright_wrapper.PlaywrightController")
    mocker.patch("src.replay.engine.PlaywrightController", mock_class)
    mocker.patch("src.agent.discovery.PlaywrightController", mock_class)
    instance = mock_class.return_value
    instance.execute_action.return_value = "mocked_extracted_text"
    instance.check_element_exists.return_value = False
    return instance

@pytest.fixture
def mock_anthropic(mocker):
    """Mocks the Anthropic client to return deterministic JSON strings."""
    mock_client_discovery = mocker.patch("src.agent.discovery.Anthropic")
    mock_client_classifier = mocker.patch("src.agent.classifier.Anthropic")
    
    instance = mock_client_discovery.return_value
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = '{"action": "wait", "value": "DONE"}'
    mock_response.content = [mock_block]
    instance.messages.create.return_value = mock_response
    
    # Mirror for classifier
    mock_client_classifier.return_value.messages.create.return_value = mock_response
    return instance

@pytest.fixture
def mock_fs(mocker):
    """Mocks built-in open for safe file system assertions."""
    mocker.patch("os.makedirs")
    return mocker.patch("builtins.open", mocker.mock_open(read_data='{"version": 1, "steps": []}'))

import yaml
import os

REAL_CONFIG = {}
if os.path.exists("config.yaml"):
    with open("config.yaml", "r", encoding="utf-8") as f:
        REAL_CONFIG = yaml.safe_load(f)

@pytest.fixture(autouse=True)
def mock_yaml(mocker):
    """Mocks yaml.safe_load to return real config values to prevent KeyError"""
    return mocker.patch("yaml.safe_load", return_value=REAL_CONFIG)

@pytest.fixture(autouse=True)
def mock_input(mocker):
    """Mocks built-in input to prevent tests hanging on manual input"""
    return mocker.patch("builtins.input", return_value="mock_error")
