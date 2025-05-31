from typing import List, Dict, Optional
from pydantic import BaseModel

class UserPreferences(BaseModel):
    """Model for storing user meal planning preferences."""
    meal_count: int
    dietary_restrictions: List[str]
    cuisine_preferences: List[str]
    cooking_days: List[str]
    servings_per_meal: int = 1

def collect_dietary_restrictions() -> List[str]:
    """
    Tool for collecting dietary restrictions from user input.
    Returns a list of dietary restrictions.
    """
    # This will be called by the agent to collect dietary restrictions
    return []

def collect_meal_count() -> int:
    """
    Tool for collecting the number of meals needed.
    Returns the number of meals to plan.
    """
    # This will be called by the agent to collect meal count
    return 0

def collect_cooking_days() -> List[str]:
    """
    Tool for collecting days available for cooking.
    Returns a list of days.
    """
    # This will be called by the agent to collect cooking days
    return []

def collect_cuisine_preferences() -> List[str]:
    """
    Tool for collecting cuisine preferences.
    Returns a list of preferred cuisines.
    """
    # This will be called by the agent to collect cuisine preferences
    return []

def validate_preferences(preferences: UserPreferences) -> bool:
    """
    Validates that all user preferences are properly set.
    Returns True if valid, False otherwise.
    """
    return (
        preferences.meal_count > 0
        and len(preferences.cooking_days) > 0
        and preferences.servings_per_meal > 0
    ) 