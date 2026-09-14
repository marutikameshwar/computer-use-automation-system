import pytest
from pydantic import ValidationError
from src.schema.models import Step, Locator, ExpectedBusinessOutcome, CapabilityArtifact

@pytest.mark.unit
def test_valid_step_parsing():
    json_data = '{"action": "click", "locator": {"strategy": "role", "value": "button", "name": "Submit"}, "value": null, "extract_as": null}'
    step = Step.model_validate_json(json_data)
    assert step.action == "click"
    assert step.locator.name == "Submit"
    assert step.locator.strategy == "role"

@pytest.mark.unit
def test_invalid_step_action():
    json_data = '{"action": "fly", "value": null}'
    with pytest.raises(ValidationError):
        Step.model_validate_json(json_data)

@pytest.mark.unit
def test_business_outcome_severity():
    json_data = '{"name": "test", "severity": "invalid_severity", "locator": {"strategy": "text", "value": "err"}}'
    with pytest.raises(ValidationError):
        ExpectedBusinessOutcome.model_validate_json(json_data)

@pytest.mark.unit
def test_capability_artifact_validation():
    json_data = '''
    {
      "version": 1,
      "name": "Test",
      "description": "Test Desc",
      "inputs": [],
      "steps": [],
      "success_condition": {"strategy": "text", "value": "Success"}
    }
    '''
    artifact = CapabilityArtifact.model_validate_json(json_data)
    assert artifact.version == 1
    assert artifact.success_condition.value == "Success"
