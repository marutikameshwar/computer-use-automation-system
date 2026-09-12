import json
from playwright.sync_api import sync_playwright, Page, Browser

class PlaywrightController:
    """
    A wrapper around Playwright specifically designed to support AI agent operations.
    It exposes the Accessibility Tree to the AI, and executes strict actions.
    """
    def __init__(self):
        self.playwright = sync_playwright().start()
        # We run headless=False so you can watch the AI control the browser!
        self.browser = self.playwright.chromium.launch(headless=False)
        self.page = self.browser.new_page()

    def goto(self, url: str):
        print(f"[Controller] Navigating to {url}")
        self.page.goto(url)
        self.page.wait_for_load_state('networkidle')

    def get_accessibility_tree(self) -> str:
        """
        Extracts the ARIA snapshot of the current page.
        This is perfectly formatted for Claude. It removes all CSS/div noise and 
        only shows meaningful interactable elements (roles, names, text).
        """
        return self.page.aria_snapshot()

    def execute_action(self, action: str, locator_strategy: str, locator_value: str, locator_name: str = None, input_value: str = None):
        """
        Executes an action passed down from the AI's Step model.
        """
        print(f"[Controller] Executing: {action} on {locator_strategy}='{locator_value}' (name='{locator_name}')")
        
        # 1. Resolve the element based on the locator
        if not locator_value:
            raise ValueError("Locator value is missing!")

        if locator_strategy == "role":
            if locator_name:
                element = self.page.get_by_role(locator_value, name=locator_name)
            else:
                element = self.page.get_by_role(locator_value)
        elif locator_strategy == "text" or locator_strategy == "exact_text":
            element = self.page.get_by_text(locator_value, exact=(locator_strategy=="exact_text"))
        elif locator_strategy == "label":
            element = self.page.get_by_label(locator_value)
        elif locator_strategy == "placeholder":
            element = self.page.get_by_placeholder(locator_value)
        else:
            raise ValueError(f"Unsupported locator strategy: {locator_strategy}")

        # 2. Execute the requested action
        if action == "click":
            element.first.click()
        elif action == "type":
            element.first.fill(input_value)
        elif action == "check":
            element.first.check()
        elif action == "read_text":
            return element.first.inner_text()
        else:
            raise ValueError(f"Unsupported action: {action}")
        
        # Wait for any network requests to finish before letting the AI observe again
        self.page.wait_for_load_state('networkidle')

    def close(self):
        self.browser.close()
        self.playwright.stop()
