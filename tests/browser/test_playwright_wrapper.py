import pytest
import os
from unittest.mock import MagicMock
from src.browser.playwright_wrapper import PlaywrightController

@pytest.fixture
def mock_sync_playwright(mocker):
    # Mock playwright's sync_playwright completely
    mock_sp = mocker.patch("src.browser.playwright_wrapper.sync_playwright")
    mock_playwright = mock_sp.return_value.start.return_value
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_page = mock_browser.new_page.return_value
    return mock_page

@pytest.mark.unit
def test_playwright_init(mock_sync_playwright):
    controller = PlaywrightController()
    assert controller.playwright is not None
    assert controller.browser is not None
    assert controller.page is not None

@pytest.mark.unit
def test_goto_allowed_domain(mock_sync_playwright):
    controller = PlaywrightController()
    controller.goto("http://localhost:5000/dashboard")
    mock_sync_playwright.goto.assert_called_with("http://localhost:5000/dashboard")
    mock_sync_playwright.wait_for_load_state.assert_called_with("networkidle")

@pytest.mark.unit
def test_goto_blocked_domain(mock_sync_playwright):
    controller = PlaywrightController()
    with pytest.raises(PermissionError) as exc:
        controller.goto("http://evil.com")
    assert "blocked by Allowlist" in str(exc.value)

@pytest.mark.unit
def test_get_accessibility_tree(mock_sync_playwright):
    mock_sync_playwright.aria_snapshot.return_value = "mock_aria"
    controller = PlaywrightController()
    assert controller.get_accessibility_tree() == "mock_aria"

@pytest.mark.unit
def test_redact_sensitive_data(mock_sync_playwright):
    controller = PlaywrightController()
    assert controller.redact_sensitive_data("my secret") == "[REDACTED]"
    assert controller.redact_sensitive_data("") == ""
    assert controller.redact_sensitive_data(None) is None

@pytest.mark.unit
def test_execute_action_blocked(mock_sync_playwright):
    controller = PlaywrightController()
    with pytest.raises(PermissionError):
        controller.execute_action("hack", "role", "button")

@pytest.mark.unit
def test_execute_action_navigate(mock_sync_playwright):
    controller = PlaywrightController()
    controller.execute_action("navigate", None, None, input_value="http://localhost:5000")
    mock_sync_playwright.goto.assert_called_with("http://localhost:5000")

@pytest.mark.unit
def test_execute_action_missing_locator(mock_sync_playwright):
    controller = PlaywrightController()
    with pytest.raises(ValueError) as exc:
        controller.execute_action("click", "role", None)
    assert "Locator value is missing" in str(exc.value)

@pytest.mark.unit
def test_execute_action_role_locator(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    controller.execute_action("click", "role", "button", locator_name="Submit")
    mock_sync_playwright.get_by_role.assert_called_with("button", name="Submit")
    mock_locator.first.click.assert_called_once()

@pytest.mark.unit
def test_execute_action_text_locator(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_text.return_value = mock_locator
    
    controller.execute_action("click", "text", "Login")
    mock_sync_playwright.get_by_text.assert_called_with("Login", exact=False)

@pytest.mark.unit
def test_execute_action_label_locator(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_label.return_value = mock_locator
    
    controller.execute_action("click", "label", "Username")
    mock_sync_playwright.get_by_label.assert_called_with("Username")

@pytest.mark.unit
def test_execute_action_placeholder_locator(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_placeholder.return_value = mock_locator
    
    controller.execute_action("click", "placeholder", "Password")
    mock_sync_playwright.get_by_placeholder.assert_called_with("Password")

@pytest.mark.unit
def test_execute_action_type(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    controller.execute_action("type", "role", "textbox", input_value="hello")
    mock_locator.first.fill.assert_called_with("hello")

@pytest.mark.unit
def test_execute_action_check(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    controller.execute_action("check", "role", "checkbox")
    mock_locator.first.check.assert_called_once()

@pytest.mark.unit
def test_execute_action_read_text(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.first.inner_text.return_value = "hello world"
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    result = controller.execute_action("read_text", "role", "article")
    assert result == "hello world"

@pytest.mark.unit
def test_take_screenshot(mock_sync_playwright):
    controller = PlaywrightController()
    controller.take_screenshot("test.png")
    mock_sync_playwright.screenshot.assert_called_with(path="test.png")

@pytest.mark.unit
def test_check_element_exists_role(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.is_visible.return_value = True
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    assert controller.check_element_exists("role", "button", name="OK") == True
    mock_sync_playwright.get_by_role.assert_called_with("button", name="OK")

@pytest.mark.unit
def test_check_element_exists_text(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.is_visible.return_value = False
    mock_sync_playwright.get_by_text.return_value = mock_locator
    
    assert controller.check_element_exists("text", "Not Found") == False

@pytest.mark.unit
def test_check_element_exists_label(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.is_visible.return_value = True
    mock_sync_playwright.get_by_label.return_value = mock_locator
    
    assert controller.check_element_exists("label", "Email") == True

@pytest.mark.unit
def test_check_element_exists_placeholder(mock_sync_playwright):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.is_visible.return_value = True
    mock_sync_playwright.get_by_placeholder.return_value = mock_locator
    
    assert controller.check_element_exists("placeholder", "Email") == True

@pytest.mark.unit
def test_check_element_exists_exception(mock_sync_playwright):
    controller = PlaywrightController()
    mock_sync_playwright.get_by_role.side_effect = Exception("Browser closed")
    assert controller.check_element_exists("role", "button") == False

@pytest.mark.unit
def test_close(mock_sync_playwright, mocker):
    mock_sp = mocker.patch("src.browser.playwright_wrapper.sync_playwright")
    mock_playwright = mock_sp.return_value.__enter__.return_value
    
    controller = PlaywrightController()
    controller.close()
    
    controller.browser.close.assert_called_once()
    controller.playwright.stop.assert_called_once()

@pytest.mark.unit
def test_risky_action_prompt(mock_sync_playwright, mocker):
    controller = PlaywrightController()
    mock_locator = MagicMock()
    mock_locator.first.is_visible.return_value = True
    mock_sync_playwright.get_by_role.return_value = mock_locator
    
    mock_input = mocker.patch("builtins.input", return_value="")
    
    controller.execute_action("click", "role", "button", locator_name="Submit Transfer")
    
    # Should have prompted for input since "submit" and "transfer" are risky
    mock_input.assert_called_once()
    mock_locator.first.click.assert_called_once()
