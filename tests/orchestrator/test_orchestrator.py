import pytest
from src.orchestrator.orchestrator import Orchestrator

@pytest.mark.integration
def test_resolve_version_no_pointer(mock_fs, mocker):
    mocker.patch("os.path.exists", return_value=False)
    orchestrator = Orchestrator("test_cap")
    assert orchestrator.resolve_version() is None

@pytest.mark.integration
def test_resolve_version_with_pointer(mock_fs, mocker):
    # Mock exists to true for both pointer and artifact
    mocker.patch("os.path.exists", return_value=True)
    orchestrator = Orchestrator("test_cap")
    path = orchestrator.resolve_version()
    # mock_fs (builtins.open mock) returns "1" (from conftest.py) for the version
    # Actually conftest returns JSON data for open mock. We need to mock open explicitly here
    mock_open = mocker.patch("builtins.open", mocker.mock_open(read_data="1"))
    path = orchestrator.resolve_version()
    assert "v1.json" in path

@pytest.mark.integration
def test_run_discovery(mock_anthropic, mock_playwright, mock_fs, mocker):
    # Ensure it writes the artifact
    orchestrator = Orchestrator("test_cap")
    orchestrator.run_discovery("goal", "url")
    mock_fs.assert_called()

@pytest.mark.integration
def test_run_replay(mock_anthropic, mock_playwright, mock_fs, mocker):
    # Mock ReplayEngine
    mock_engine = mocker.patch("src.orchestrator.orchestrator.ReplayEngine", autospec=True)
    mock_engine.return_value.run.return_value = {"status": "success"}
    orchestrator = Orchestrator("test_cap")
    orchestrator.run_replay("123", "url", "v1.json")
    mock_engine.return_value.run.assert_called_once()
