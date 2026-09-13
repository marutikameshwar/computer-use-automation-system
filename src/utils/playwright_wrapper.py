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
        # Domain Allowlist Check (Phase 7)
        if not url.startswith("http://localhost:5000"):
            raise PermissionError(f"Navigation to unauthorized domain blocked by Allowlist: {url}")
            
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

    def redact_sensitive_data(self, text: str) -> str:
        """
        Redacts standard alphanumeric inputs to prevent PII leakage in logs.
        """
        if not text:
            return text
        # If it's a number, SSN, or standard input text, we redact it.
        # In a real app we might use regex to detect SSNs, but here we redact all typing to be safe.
        return "[REDACTED]"
        
    def execute_action(self, action: str, locator_strategy: str, locator_value: str, locator_name: str = None, input_value: str = None):
        """
        Executes an action passed down from the AI's Step model.
        """
        display_value = self.redact_sensitive_data(input_value) if action == "type" else input_value
        print(f"[Controller] Executing: {action} on {locator_strategy}='{locator_value}' (name='{locator_name}') with value='{display_value}'")
        
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
            # --- Guardrail: Risky Action Check ---
            risky_keywords = ["submit", "transfer", "delete", "pay", "transact"]
            # Check if locator_name or locator_value contains a risky keyword (case-insensitive)
            name_lower = str(locator_name).lower() if locator_name else ""
            val_lower = str(locator_value).lower() if locator_value else ""
            
            if any(keyword in name_lower or keyword in val_lower for keyword in risky_keywords):
                print(f"\n[Guardrail] RISKY ACTION DETECTED: You are about to click '{locator_name or locator_value}'.")
                input("[Guardrail] Press Enter to approve and continue...")
                print("[Guardrail] Action approved. Proceeding...")
            # -------------------------------------
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

    def take_screenshot(self, filepath: str):
        self.page.screenshot(path=filepath)
        
    def check_element_exists(self, strategy: str, value: str, name: str = None) -> bool:
        """
        Non-blocking check to see if an element exists on the screen.
        Used for checking Expected Business Outcomes.
        """
        try:
            if strategy == "role":
                if name:
                    return self.page.get_by_role(value, name=name).is_visible(timeout=500)
                return self.page.get_by_role(value).is_visible(timeout=500)
            elif strategy == "text" or strategy == "exact_text":
                return self.page.get_by_text(value, exact=(strategy=="exact_text")).is_visible(timeout=500)
            elif strategy == "label":
                return self.page.get_by_label(value).is_visible(timeout=500)
            elif strategy == "placeholder":
                return self.page.get_by_placeholder(value).is_visible(timeout=500)
            return False
        except Exception:
            return False

    def close(self):
        self.browser.close()
        self.playwright.stop()
