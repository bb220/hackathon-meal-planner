from typing import List, Dict, Optional, Tuple
from tools.recipe import Recipe

def calculate_optimal_servings_distribution(recipes: List[Recipe], total_servings_needed: int) -> List[float]:
    """
    Calculate optimal multipliers for each recipe to meet total servings needed with minimal excess.
    
    Args:
        recipes: List of recipes to adjust
        total_servings_needed: Total servings needed for the week
        
    Returns:
        List of multipliers for each recipe
    """
    # Get base servings for each recipe
    base_servings = [recipe.servings for recipe in recipes]
    
    # Calculate initial multipliers needed to meet servings per meal
    initial_multipliers = [1.0 for _ in recipes]
    total_servings = sum(s * m for s, m in zip(base_servings, initial_multipliers))
    
    # If we need more servings, scale up proportionally
    if total_servings < total_servings_needed:
        scale_factor = total_servings_needed / total_servings
        return [m * scale_factor for m in initial_multipliers]
    
    # If we have too many servings, try to scale down while keeping reasonable portions
    return initial_multipliers

def calculate_servings_multiplier(recipe: Recipe, servings_needed: int) -> float:
    """Calculate the multiplier needed to scale recipe servings."""
    return servings_needed / recipe.servings

class ShoppingList:
    """Class to manage shopping list generation."""
    
    def __init__(self):
        self.items = {}  # Dictionary to store consolidated ingredients
    
    def add_recipe(self, recipe: Recipe, servings_multiplier: float = 1.0):
        """Add a recipe's ingredients to the shopping list."""
        for ingredient in recipe.ingredients:
            # Convert ingredient to lowercase for consistent matching
            food = ingredient.food.lower()
            
            # Calculate scaled quantity
            try:
                quantity = float(ingredient.quantity) * servings_multiplier
            except (ValueError, TypeError):
                # If quantity can't be converted to float, use original string
                quantity = ingredient.quantity
            
            # Get measure and category
            measure = ingredient.measure or "unit"
            category = ingredient.foodCategory or "Other"
            
            # Create key for ingredient matching
            key = (food, measure)
            
            if key in self.items:
                # If quantity is numeric, add it
                if isinstance(self.items[key]["quantity"], (int, float)) and isinstance(quantity, (int, float)):
                    self.items[key]["quantity"] += quantity
                else:
                    # If either quantity is a string, concatenate with a note
                    self.items[key]["quantity"] = f"{self.items[key]['quantity']} + {quantity}"
            else:
                self.items[key] = {
                    "food": food,
                    "quantity": quantity,
                    "measure": measure,
                    "category": category
                }
    
    def clear(self):
        """Clear the shopping list."""
        self.items = {}
    
    def get_consolidated_list(self) -> List[Dict[str, str]]:
        """Get the consolidated shopping list."""
        shopping_list = []
        for item_data in self.items.values():
            quantity = item_data["quantity"]
            if isinstance(quantity, float):
                # Round to 2 decimal places and remove trailing zeros
                quantity_str = f"{quantity:.2f}".rstrip('0').rstrip('.')
            else:
                quantity_str = str(quantity)
            
            shopping_list.append({
                "food": item_data["food"].title(),  # Capitalize food names
                "quantity": quantity_str,
                "measure": item_data["measure"],
                "category": item_data["category"]
            })
        
        return sorted(shopping_list, key=lambda x: (x["category"], x["food"])) 