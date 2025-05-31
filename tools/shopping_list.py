from typing import List, Dict
from .recipe import Recipe

class ShoppingList:
    """Handles generation and management of shopping lists from recipes."""
    
    def __init__(self):
        self.items: Dict[str, Dict[str, float]] = {}  # food -> {measure -> quantity}
        
    def add_recipe(self, recipe: Recipe, servings_multiplier: float = 1.0):
        """
        Add a recipe's ingredients to the shopping list.
        
        Args:
            recipe: Recipe object containing ingredients
            servings_multiplier: Factor to multiply ingredient quantities by
        """
        for ingredient in recipe.ingredients:
            food = ingredient["food"].lower()
            measure = ingredient["measure"].lower()
            quantity = float(ingredient["quantity"]) * servings_multiplier
            
            if food not in self.items:
                self.items[food] = {}
            
            if measure in self.items[food]:
                self.items[food][measure] += quantity
            else:
                self.items[food][measure] = quantity
    
    def get_consolidated_list(self) -> List[Dict[str, str]]:
        """
        Get a consolidated list of all ingredients with their quantities.
        
        Returns:
            List of dictionaries containing food items and their quantities
        """
        consolidated = []
        for food, measures in self.items.items():
            for measure, quantity in measures.items():
                # Round to 2 decimal places for cleaner numbers
                rounded_quantity = round(quantity, 2)
                consolidated.append({
                    "food": food,
                    "quantity": str(rounded_quantity),
                    "measure": measure
                })
        
        # Sort by food name for easier reading
        return sorted(consolidated, key=lambda x: x["food"])
    
    def clear(self):
        """Clear the shopping list."""
        self.items.clear()

def calculate_servings_multiplier(recipe: Recipe, desired_servings: int) -> float:
    """
    Calculate the multiplier needed to scale a recipe to the desired number of servings.
    
    Args:
        recipe: Recipe object
        desired_servings: Number of servings needed
        
    Returns:
        Float multiplier to scale recipe quantities
    """
    return desired_servings / recipe.servings 