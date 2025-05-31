from typing import List, Dict, Optional
from tools.recipe import Recipe

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
        # Convert quantities to strings with reasonable precision
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