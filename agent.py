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
            print("\nCollecting your preferences...")
            self.user_preferences = await self._collect_user_preferences()
            
            # Step 2: Search for recipes
            print("\nSearching for recipes that match your preferences...")
            recipes = await self._search_recipes()
            
            # Step 3: Let user select recipes
            print("\nFinding the best recipe matches...")
            selected_recipes = await self._get_recipe_selections(recipes)
            
            # Step 4: Generate shopping list
            print("\nGenerating your shopping list...")
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
             2. Cuisine preferences (Italian, Mexican, Asian, etc.)
             3. Any dietary restrictions (vegetarian, vegan, gluten-free, etc.)
             4. Days they're available to cook
             5. Number of servings per meal
             
             Be friendly and conversational, but also efficient in collecting the information.
             After collecting all information, summarize it and ask for confirmation.
             When the user confirms, do not show a JSON summary or ask for further input.
             Instead, just say "Great! Let me search for recipes that match your preferences..."
             """},
            {"role": "user", "content": "I need help planning my meals for the week."}
        ]
        
        # Initialize preferences with default values
        preferences = None
        while preferences is None:
            # Get next message from OpenAI
            response = self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                temperature=0.7
            )
            
            # Print assistant's message
            assistant_message = response.choices[0].message.content
            print("\nAssistant:", assistant_message)
            
            # If this is the transition message, extract preferences
            if "search for recipes" in assistant_message.lower():
                # Extract final preferences
                extraction_messages = [
                    {"role": "system", "content": """You are a JSON extraction expert. Extract the meal planning preferences from the conversation and format them EXACTLY as shown:
                     {
                         "meal_count": <integer>,
                         "dietary_restrictions": [<string>, ...],
                         "cuisine_preferences": [<string>, ...],
                         "cooking_days": [<string>, ...],
                         "servings_per_meal": <integer>
                     }
                     
                     Rules:
                     1. meal_count and servings_per_meal must be integers
                     2. All arrays must be properly formatted, even if empty
                     3. If no dietary restrictions, use empty array []
                     4. Convert "none" or "no restrictions" to empty array
                     5. Ensure all strings are properly quoted
                     6. Use exact field names as shown
                     
                     Example:
                     {
                         "meal_count": 5,
                         "dietary_restrictions": [],
                         "cuisine_preferences": ["Italian", "Mexican"],
                         "cooking_days": ["Monday", "Wednesday"],
                         "servings_per_meal": 2
                     }"""},
                    {"role": "user", "content": str(messages[:-2])}  # Exclude the last confirmation exchange
                ]
                
                try:
                    extraction_response = self.client.chat.completions.create(
                        model=settings.MODEL_NAME,
                        messages=extraction_messages,
                        temperature=0
                    )
                    
                    import json
                    extracted_text = extraction_response.choices[0].message.content.strip()
                    
                    # Find the JSON object in the response
                    start_idx = extracted_text.find('{')
                    end_idx = extracted_text.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = extracted_text[start_idx:end_idx]
                        preferences = json.loads(json_str)
                        
                        # Convert "none" to empty array for dietary restrictions
                        if isinstance(preferences["dietary_restrictions"], str):
                            if preferences["dietary_restrictions"].lower() in ["none", "no restrictions"]:
                                preferences["dietary_restrictions"] = []
                        
                        # Validate the extracted preferences
                        if not self._is_preferences_complete(preferences):
                            print("\nI apologize, but I couldn't properly capture all your preferences. Let's try again.")
                            preferences = None
                    else:
                        print("\nI apologize, but I couldn't properly extract your preferences. Let's try again.")
                        preferences = None
                except json.JSONDecodeError as e:
                    print(f"\nError parsing preferences: {str(e)}")
                    preferences = None
                except Exception as e:
                    print(f"\nUnexpected error while extracting preferences: {str(e)}")
                    preferences = None
                break  # Exit the loop if we got the transition message
            
            # Get user's response
            user_response = input("\nYou: ").strip()
            
            # Add messages to conversation
            messages.append({"role": "assistant", "content": assistant_message})
            messages.append({"role": "user", "content": user_response})
            
            # If user confirmed, instruct assistant to proceed to recipe search
            if "yes" in user_response.lower() or "correct" in user_response.lower() or "looks good" in user_response.lower():
                messages.append({
                    "role": "system",
                    "content": "The user has confirmed. Respond ONLY with: 'Great! Let me search for recipes that match your preferences...'"
                })
        
        if preferences is None:
            raise ValueError("Failed to collect valid preferences")
            
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
            cuisine_type=self.user_preferences.cuisine_preferences,
            meal_type=["lunch/dinner"],  # Default to dinner recipes
            dish_type=["main course"]    # Focus on main dishes
        )
    
    async def _get_recipe_selections(self, recipes: List[Recipe]) -> List[Recipe]:
        """Present recipes to user and get their selections."""
        if not recipes:
            print("\nNo recipes found matching your criteria. Please try again with different preferences.")
            return []

        # Present recipes to user
        print("\nHere are some recipes that match your preferences:")
        for i, recipe in enumerate(recipes, 1):
            servings_info = f"(Makes {recipe.servings} servings)"
            cooking_time = f", {recipe.total_time} minutes" if recipe.total_time else ""
            print(f"\n{i}. {recipe.name} {servings_info}{cooking_time}")
            print(f"   Cuisine: {', '.join(recipe.cuisine_type) if recipe.cuisine_type else 'Not specified'}")
            print(f"   Link: {recipe.url}")

        messages = [
            {"role": "system", "content": """You are a helpful meal planning assistant.
             Help the user select recipes from the list. Keep track of:
             1. Total number of servings needed
             2. Which recipes they've selected
             3. Whether they have enough servings
             
             Be conversational but efficient. If they haven't selected enough servings,
             suggest they select more recipes. If they've selected too many, let them know.
             
             After the selection is complete, respond with a JSON summary of selected recipe indices."""},
            {"role": "assistant", "content": f"""I see you need {self.user_preferences.meal_count} meals 
             with {self.user_preferences.servings_per_meal} servings each, 
             for a total of {self.user_preferences.meal_count * self.user_preferences.servings_per_meal} servings.
             
             Please tell me which recipes you'd like to select by their numbers (1-{len(recipes)}).
             You can list multiple numbers separated by commas."""}
        ]

        selected_indices = set()
        total_servings = 0
        needed_servings = self.user_preferences.meal_count * self.user_preferences.servings_per_meal

        while total_servings < needed_servings:
            # Print assistant's message
            print("\nAssistant:", messages[-1]["content"])
            
            # Get user's response
            user_response = input("\nYou: ").strip()
            
            # Add user's response to messages
            messages.append({"role": "user", "content": user_response})
            
            # Extract recipe indices from response
            try:
                # Ask OpenAI to parse the response and extract recipe numbers
                extraction_messages = [
                    {"role": "system", "content": """Extract recipe numbers from the user's response.
                     Return a JSON array of integers representing the selected recipe indices.
                     Example: If user says "I'll take recipes 1, 3, and 5", return [1, 3, 5]"""},
                    {"role": "user", "content": user_response}
                ]
                
                response = self.client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=extraction_messages,
                    temperature=0
                )
                
                import json
                new_indices = set(json.loads(response.choices[0].message.content))
                
                # Validate indices
                valid_indices = {i for i in new_indices if 1 <= i <= len(recipes)}
                if not valid_indices:
                    raise ValueError("No valid recipe numbers found in response")
                
                # Add valid indices to selection
                selected_indices.update(valid_indices)
                
                # Calculate total servings
                total_servings = sum(recipes[i-1].servings for i in selected_indices)
                
                # Prepare next message based on servings status
                if total_servings < needed_servings:
                    remaining_servings = needed_servings - total_servings
                    messages.append({
                        "role": "assistant",
                        "content": f"""You've selected {len(selected_indices)} recipes providing {total_servings} servings.
                         You still need {remaining_servings} more servings to meet your goal.
                         Please select additional recipes."""
                    })
                else:
                    messages.append({
                        "role": "assistant",
                        "content": f"""Great! You've selected enough recipes to provide {total_servings} servings,
                         which meets your need for {needed_servings} servings."""
                    })
                    print("\nAssistant:", messages[-1]["content"])
                    
            except Exception as e:
                print(f"\nError parsing selection: {e}")
                messages.append({
                    "role": "assistant",
                    "content": "I didn't understand that selection. Please enter recipe numbers (1-{len(recipes)}) separated by commas."
                })

        # Return selected recipes
        return [recipes[i-1] for i in selected_indices]
    
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
        print("\n=== Your Weekly Dinner Plan ===\n")
        
        # Map recipes to days based on user preferences
        available_days = self.user_preferences.cooking_days
        recipes_by_day = {}
        
        for day, recipe in zip(available_days, recipes):
            recipes_by_day[day] = recipe
        
        # Print recipes by day
        for day in available_days:
            print(f"\n{day}:")
            if day in recipes_by_day:
                self._print_recipe_details(recipes_by_day[day])
            else:
                print("  • No recipe planned")
        
        # Print shopping list
        print("\n=== Shopping List ===\n")
        
        # Group items by food category
        categorized_items = {}
        
        for item in shopping_list:
            category = item.get("category", "Other")
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)
        
        # Print items by category
        for category, items in sorted(categorized_items.items()):
            print(f"\n{category}:")
            for item in items:
                quantity = item.get("quantity", "")
                measure = item.get("measure", "")
                food = item.get("food", "")
                print(f"  • {quantity} {measure} {food}".strip())
        
        # Print summary
        total_recipes = len(recipes)
        print(f"\nSummary:")
        print(f"• Planned dinners: {total_recipes}")
        print(f"• Cooking days: {', '.join(available_days)}")
        if self.user_preferences.dietary_restrictions:
            print(f"• Dietary restrictions: {', '.join(self.user_preferences.dietary_restrictions)}")
        print(f"• Total servings: {total_recipes * self.user_preferences.servings_per_meal}")
        print("\nEnjoy your meals! 🍽️")
    
    def _print_recipe_details(self, recipe: Recipe):
        """Helper method to print recipe details in a consistent format."""
        # Basic recipe information
        print(f"  • {recipe.name}")
        print(f"    Servings: {recipe.servings}")
        if recipe.total_time:
            print(f"    Time: {recipe.total_time} minutes")
        
        # Print cuisine type if available
        if recipe.cuisine_type:
            print(f"    Cuisine: {', '.join(recipe.cuisine_type)}")
        
        # Print diet and health labels if available
        if recipe.diet_labels:
            print(f"    Diet Labels: {', '.join(recipe.diet_labels)}")
        if recipe.health_labels:
            print(f"    Health Labels: {', '.join(recipe.health_labels[:3])}")  # Limit to top 3 health labels
        
        # Print calories if available
        if recipe.calories:
            print(f"    Calories per serving: {int(recipe.calories / recipe.servings)} kcal")
        
        # Print recipe URL
        print(f"    Recipe Link: {recipe.url}")

if __name__ == "__main__":
    import asyncio
    
    agent = MealPlannerAgent()
    asyncio.run(agent.run()) 