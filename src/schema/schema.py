from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

class Locator(BaseModel):
    """
    Defines how to find an element on the screen.
    We strictly prioritize accessibility (roles/names) and visible text 
    to remain robust against legacy UI drift, rather than brittle CSS paths.
    """
    strategy: Literal["role", "text", "placeholder", "label", "exact_text"] = Field(
        description="The strategy to use to find the element (e.g., 'role', 'text')."
    )
    value: str = Field(
        description="The primary value to search for (e.g., 'button' for role, or 'Submit' for text)."
    )
    name: Optional[str] = Field(
        default=None, 
        description="The accessible name. Used when strategy is 'role' (e.g., role='button', name='Submit')."
    )

class Step(BaseModel):
    """
    A single deterministic action to take on the UI.
    """
    action: Literal["click", "type", "navigate", "read_text", "check", "wait"] = Field(
        description="The action to perform."
    )
    locator: Optional[Locator] = Field(
        default=None, 
        description="How to find the element to act on. (Can be null if action is 'navigate')."
    )
    value: Optional[str] = Field(
        default=None, 
        description="The text to type (if action is 'type') or URL to navigate to."
    )
    extract_as: Optional[str] = Field(
        default=None, 
        description="If action is 'read_text', the key name to store the extracted data under in the outputs."
    )

class ExpectedBusinessOutcome(BaseModel):
    """
    A legitimate, expected alternate state.
    (e.g., Searching for an invalid user returns a 'Record not found' banner, not a crash).
    """
    name: str = Field(
        description="A machine-readable name for the outcome (e.g., 'record_not_found')."
    )
    locator: Locator = Field(
        description="The specific UI element that confirms this business outcome occurred."
    )

class CapabilityArtifact(BaseModel):
    """
    The strict contract between the Discovery Agent and the Replay Engine.
    This is the JSON file saved to disk after a successful discovery run.
    """
    version: str = Field(default="1.0", description="Schema version.")
    name: str = Field(description="A descriptive name for this capability.")
    description: str = Field(description="A natural language description of what this automation does.")
    
    inputs: List[str] = Field(
        description="List of input parameter keys required to run this (e.g., ['member_id', 'amount'])."
    )
    outputs: List[str] = Field(
        default_factory=list,
        description="List of data keys that will be extracted and returned to the caller."
    )
    
    steps: List[Step] = Field(
        description="The strict, ordered sequence of UI actions to execute."
    )
    
    success_condition: Locator = Field(
        description="The final UI element that proves the automation completed its goal successfully."
    )
    expected_outcomes: List[ExpectedBusinessOutcome] = Field(
        default_factory=list, 
        description="A list of known business outcomes to check for if an error occurs during execution."
    )
