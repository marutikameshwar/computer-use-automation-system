import pytest
from src.replay.engine import ReplayEngine
from src.schema.models import CapabilityArtifact

@pytest.fixture
def mock_artifact():
    return CapabilityArtifact.model_validate({
        "version": 1,
        "name": "Test",
        "description": "Test",
        "inputs": ["test_input"],
        "steps": [
            {"action": "type", "locator": {"strategy": "role", "value": "textbox", "name": "input"}, "value": "{{test_input}}", "extract_as": None}
        ],
        "success_condition": {"strategy": "text", "value": "Success"},
        "expected_outcomes": []
    })

@pytest.mark.integration
def test_engine_happy_path(mock_fs, mock_playwright, mock_artifact, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact)
    engine = ReplayEngine("dummy_path.json", "dummy_dir")
    
    # Mock check_element_exists to return False initially, then True for success condition
    mock_playwright.check_element_exists.side_effect = [False, True]
    
    result = engine.run("http://localhost", {"test_input": "hello"})
    
    assert result["status"] == "success"
    # Verify that the parameter injection worked (swapped {{test_input}} with "hello")
    call_args = mock_playwright.execute_action.call_args
    assert call_args[1]["action"] == "type"
    assert call_args[1]["input_value"] == "hello"

@pytest.mark.integration
def test_engine_failure_triggers_classifier(mock_fs, mock_playwright, mock_artifact, mock_anthropic, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact)
    mocker.patch("src.replay.engine.ArtifactWriter.write_new_version")
    
    engine = ReplayEngine("dummy_path.json", "dummy_dir")
    
    # Mock action failure
    mock_playwright.execute_action.side_effect = TimeoutError("Element not found")
    
    result = engine.run("http://localhost", {"test_input": "hello"})
    
    assert result["status"] == "escalated"
