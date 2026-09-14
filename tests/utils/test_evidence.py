import pytest
import os
from unittest.mock import patch
from datetime import datetime
from src.utils.evidence import generate_screenshot_path

@pytest.mark.unit
@patch("src.utils.evidence.datetime")
@patch("src.utils.evidence.os.makedirs")
@patch("src.utils.evidence.os.path.exists", return_value=False)
def test_generate_screenshot_path(mock_exists, mock_makedirs, mock_datetime):
    # Freeze time
    mock_datetime.now.return_value = datetime(2026, 9, 14, 12, 0, 0)
    
    path = generate_screenshot_path("test-crash!@#")
    
    # Check if makedirs was called since exists returns False
    mock_makedirs.assert_called_once()
    
    # Check if prefix was sanitized properly and timestamp appended
    expected_filename = "test_crash____20260914_120000.png"
    assert expected_filename in path
    assert "src" in path
    assert "evidence" in path
