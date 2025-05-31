from typing import List, Dict, Any
import openai
from config import settings
from tools.user_input import UserPreferences
from tools.recipe import RecipeAPI, Recipe
from tools.shopping_list import ShoppingList, calculate_servings_multiplier

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY

class MealPlannerAgent:
    """Main agent class for meal planning."""
    
    def __init__(self):
        self.recipe_api = RecipeAPI()
        self.shopping_list = ShoppingList()
        self.user_preferences = None
        self.client = openai.OpenAI()
        
    async def run(self):
        """Main execution flow for the meal planning agent."""
        try:
            # Validate environment
            settings.validate_settings()
            
            # Step 1: Collect user preferences
            self.user_preferences = await self._collect_user_preferences()
            
            # Step 2: Search for recipes
            recipes = await self._search_recipes()
            
            # Step 3: Let user select recipes
            selected_recipes = await self._get_recipe_selections(recipes)
            
            # Step 4: Generate shopping list
            shopping_list = await self._generate_shopping_list(selected_recipes)
            
            # Present results to user
            await self._present_results(selected_recipes, shopping_list)
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise
    
    async def _collect_user_preferences(self) -> UserPreferences:
        """Collect and validate user preferences through natural conversation."""
        messages = [
            {"role": "system", "content": """You are a helpful meal planning assistant. 
             Collect the following information from the user in a conversational way:
             1. Number of meals they need for the week
             2. Any dietary restrictions (vegetarian, vegan, gluten-free, etc.)
             3. Cuisine preferences (Italian, Mexican, Asian, etc.)
             4. Days they're available to cook
             5. Number of servings per meal
             
             Be friendly and conversational, but also efficient in collecting the information.
             After collecting all information, respond with a JSON summary."""},
            {"role": "user", "content": "I need help planning my meals for the week."}
        ]
        
        # Initialize preferences with default values
        preferences = {
            "meal_count": 0,
            "dietary_restrictions": [],
            "cuisine_preferences": [],
            "cooking_days": [],
            "servings_per_meal": 1
        }
        
        # Collect information through conversation
        while not self._is_preferences_complete(preferences):
            # Get next message from OpenAI
            response = self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                temperature=0.7
            )
            
            # Print assistant's message
            assistant_message = response.choices[0].message.content
            print("\nAssistant:", assistant_message)
            
            # Get user's response
            user_response = input("\nYou: ").strip()
            
            # Add messages to conversation
            messages.append({"role": "assistant", "content": assistant_message})
            messages.append({"role": "user", "content": user_response})
            
            # Try to extract preferences from the conversation
            try:
                preferences = self._extract_preferences(messages)
            except Exception as e:
                print(f"Error extracting preferences: {e}")
        
        # Create and return UserPreferences object
        return UserPreferences(
            meal_count=preferences["meal_count"],
            dietary_restrictions=preferences["dietary_restrictions"],
            cuisine_preferences=preferences["cuisine_preferences"],
            cooking_days=preferences["cooking_days"],
            servings_per_meal=preferences["servings_per_meal"]
        )
    
    def _is_preferences_complete(self, preferences: Dict[str, Any]) -> bool:
        """Check if all required preferences have been collected."""
        return (
            preferences["meal_count"] > 0
            and len(preferences["cooking_days"]) > 0
            and preferences["servings_per_meal"] > 0
        )
    
    def _extract_preferences(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract preferences from conversation history."""
        # Ask OpenAI to extract preferences from the conversation
        extraction_messages = [
            {"role": "system", "content": """Extract meal planning preferences from the conversation.
             Return a JSON object with the following fields:
             {
                 "meal_count": int,
                 "dietary_restrictions": list of strings,
                 "cuisine_preferences": list of strings,
                 "cooking_days": list of strings,
                 "servings_per_meal": int
             }
             If a field cannot be determined, use the default values (0 for numbers, empty list for lists)."""},
            {"role": "user", "content": f"Extract preferences from this conversation:\n{str(messages)}"}
        ]
        
        response = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=extraction_messages,
            temperature=0
        )
        
        # Parse the response as JSON
        import json
        try:
            preferences = json.loads(response.choices[0].message.content)
            return preferences
        except json.JSONDecodeError:
            return {
                "meal_count": 0,
                "dietary_restrictions": [],
                "cuisine_preferences": [],
                "cooking_days": [],
                "servings_per_meal": 1
            }
    
    async def _search_recipes(self) -> List[Recipe]:
        """Search for recipes based on user preferences."""
        # Build a search query based on preferences
        query = " ".join(self.user_preferences.cuisine_preferences[:2])  # Use first two cuisine preferences
        if not query:
            query = "healthy"  # Default query if no cuisine preferences
            
        return self.recipe_api.search_recipes(
            query=query,
            diet=self.user_preferences.dietary_restrictions,
            cuisine_type=self.user_preferences.cuisine_preferences
        )
    
    async def _get_recipe_selections(self, recipes: List[Recipe]) -> List[Recipe]:
        """Present recipes to user and get their selections."""
        # TODO: Implement recipe selection conversation
        return []
    
    async def _generate_shopping_list(self, recipes: List[Recipe]) -> List[Dict[str, str]]:
        """Generate consolidated shopping list from selected recipes."""
        self.shopping_list.clear()
        
        for recipe in recipes:
            # Calculate how many servings we need from this recipe
            servings_needed = self.user_preferences.meal_count * self.user_preferences.servings_per_meal
            multiplier = calculate_servings_multiplier(recipe, servings_needed)
            
            # Add recipe to shopping list with appropriate scaling
            self.shopping_list.add_recipe(recipe, servings_multiplier=multiplier)
        
        return self.shopping_list.get_consolidated_list()
    
    async def _present_results(self, recipes: List[Recipe], shopping_list: List[Dict[str, str]]):
        """Present the final meal plan and shopping list to the user."""
        # TODO: Implement results presentation
        pass

if __name__ == "__main__":
    import asyncio
    
    agent = MealPlannerAgent()
    asyncio.run(agent.run()) 