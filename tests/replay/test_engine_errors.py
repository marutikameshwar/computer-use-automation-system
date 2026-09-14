import pytest
from unittest.mock import MagicMock
from src.replay.engine import ReplayEngine
from src.schema.models import CapabilityArtifact, ExpectedBusinessOutcome, Step, Locator

@pytest.fixture
def mock_artifact_with_outcomes():
    return CapabilityArtifact(
        version=1,
        name="Test With Outcomes",
        description="Test",
        inputs=[],
        steps=[
            Step(action="click", locator=Locator(strategy="role", value="button"))
        ],
        success_condition=Locator(strategy="text", value="Done"),
        expected_outcomes=[
            ExpectedBusinessOutcome(
                name="Success Outcome",
                severity="business_outcome",
                locator=Locator(strategy="text", value="Done")
            ),
            ExpectedBusinessOutcome(
                name="Recoverable",
                severity="recoverable_condition",
                locator=Locator(strategy="text", value="Error"),
                recovery_action=Step(action="click", locator=Locator(strategy="role", value="retry-button"))
            ),
            ExpectedBusinessOutcome(
                name="Hard Fail",
                severity="hard_failure",
                locator=Locator(strategy="text", value="Fatal")
            )
        ]
    )

@pytest.mark.integration
def test_engine_business_outcome_success(mock_fs, mock_playwright, mock_artifact_with_outcomes, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact_with_outcomes)
    
    engine = ReplayEngine("dummy.json")
    
    # Force step to fail so it checks outcomes
    mock_playwright.execute_action.side_effect = Exception("Step failed")
    
    # Mock check_element_exists to return True for the "business_outcome" locator
    def check_el(strategy, value, name=None):
        if value == "Done":
            return True
        return False
    mock_playwright.check_element_exists.side_effect = check_el
    
    # Also mock screenshot to avoid file ops
    mocker.patch.object(engine, "_take_screenshot")
    
    result = engine.run("http://localhost")
    assert result["status"] == "business_outcome"
    assert result["outcome"] == "Success Outcome"

@pytest.mark.integration
def test_engine_recoverable_condition(mock_fs, mock_playwright, mock_artifact_with_outcomes, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact_with_outcomes)
    
    engine = ReplayEngine("dummy.json")
    # speed up test
    engine.config["recovery_delay_seconds"] = 0
    engine.config["step_delay_seconds"] = 0
    
    # 1. First step fails
    # 2. Recovery action fires (check_el returns True for "Error")
    # 3. Step retried and succeeds (execute_action doesn't raise exception)
    
    # Need execute_action to fail first time, then succeed
    mock_playwright.execute_action.side_effect = [Exception("Step failed"), None, None]
    
    def check_el(strategy, value, name=None):
        if value == "Error":
            return True
        return False
    mock_playwright.check_element_exists.side_effect = check_el
    
    mocker.patch.object(engine, "_take_screenshot")
    
    result = engine.run("http://localhost")
    assert result["status"] == "success"

@pytest.mark.integration
def test_engine_max_retries_exceeded(mock_fs, mock_playwright, mock_artifact_with_outcomes, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact_with_outcomes)
    
    engine = ReplayEngine("dummy.json")
    engine.config["max_retries"] = 1
    engine.config["recovery_delay_seconds"] = 0
    engine.config["step_delay_seconds"] = 0
    
    # Fails every time
    mock_playwright.execute_action.side_effect = Exception("Step failed forever")
    
    def check_el(strategy, value, name=None):
        if value == "Error":
            return True
        return False
    mock_playwright.check_element_exists.side_effect = check_el
    
    mocker.patch.object(engine, "_take_screenshot")
    
    with pytest.raises(Exception) as exc_info:
        engine.run("http://localhost")
    assert "Step failed forever" in str(exc_info.value)

@pytest.mark.integration
def test_engine_hard_failure(mock_fs, mock_playwright, mock_artifact_with_outcomes, mocker):
    mocker.patch("src.replay.engine.os.path.exists", return_value=True)
    mocker.patch("src.replay.engine.CapabilityArtifact.model_validate_json", return_value=mock_artifact_with_outcomes)
    
    engine = ReplayEngine("dummy.json")
    
    # Step fails
    mock_playwright.execute_action.side_effect = Exception("Step failed")
    
    def check_el(strategy, value, name=None):
        if value == "Fatal":
            return True
        return False
    mock_playwright.check_element_exists.side_effect = check_el
    
    # Mock escalate to return True (abort)
    mocker.patch.object(engine, "_escalate_known_failure", return_value=True)
    
    result = engine.run("http://localhost")
    assert result["status"] == "hard_failure_aborted"
    assert result["outcome"] == "Hard Fail"
