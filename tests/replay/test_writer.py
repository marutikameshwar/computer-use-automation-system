import pytest
import json
from src.schema.models import CapabilityArtifact
from src.replay.writer import ArtifactWriter

@pytest.mark.unit
def test_write_new_version(mock_fs):
    artifact_json = {
        "version": 1,
        "name": "Test",
        "description": "Test",
        "inputs": [],
        "steps": [],
        "success_condition": {"strategy": "text", "value": "Success"},
        "expected_outcomes": []
    }
    artifact = CapabilityArtifact.model_validate(artifact_json)
    
    ArtifactWriter.write_new_version(
        artifact=artifact,
        capability_dir="test_dir",
        outcome_name="test_error",
        severity="business_outcome",
        recognizer_text="Error occurred",
        recovery_action=None
    )
    
    # Check that open was called to write the new JSON and the current.txt
    mock_fs.assert_called()
    
    # Inspect the arguments passed to write to ensure the JSON was serialized correctly
    write_calls = [call.args[0] for call in mock_fs().write.call_args_list]
    
    json_written = False
    pointer_written = False
    
    for content in write_calls:
        if "test_error" in content:
            json_written = True
            written_data = json.loads(content)
            assert written_data["version"] == 2
            assert written_data["expected_outcomes"][0]["name"] == "test_error"
        if content == "2":
            pointer_written = True
            
    assert json_written
    assert pointer_written
