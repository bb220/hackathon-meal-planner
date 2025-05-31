from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from config import settings
from tools.user_input import UserPreferences
from tools.recipe import RecipeAPI, Recipe
from tools.shopping_list import ShoppingList, calculate_servings_multiplier, calculate_optimal_servings_distribution
import asyncio
import json
import os
import httpx

# Set OpenAI API key in environment
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

class MealPlannerAgent:
    """Main agent class for meal planning."""
    
    def __init__(self):
        self.recipe_api = RecipeAPI()
        self.shopping_list = ShoppingList()
        self.user_preferences = None
        
        # Create custom httpx client without proxy settings
        http_client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            timeout=httpx.Timeout(60.0),
            follow_redirects=True
        )
        
        # Initialize OpenAI client with custom http client
        self.client = AsyncOpenAI(
            http_client=http_client,
            api_key=settings.OPENAI_API_KEY
        )
        
        self.websocket = None
        self.user_input_queue = asyncio.Queue()
        self._running = True
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()
        if hasattr(self.client, 'http_client'):
            await self.client.http_client.aclose()
        
    async def send_message(self, message: str, message_type: str = "assistant"):
        """Send a message to the client."""
        if self.websocket and self._running:
            try:
                await self.websocket.send_json({
                    "type": message_type,
                    "content": message
                })
            except Exception as e:
                self._running = False
                raise
    
    async def get_user_input(self, prompt: str = None) -> str:
        """Get input from the user through websocket."""
        if prompt:
            await self.send_message(prompt)
        
        if not self._running:
            raise asyncio.CancelledError("Agent is no longer running")
            
        try:
            return await self.user_input_queue.get()
        except Exception as e:
            self._running = False
            raise
    
    async def run(self):
        """Main execution flow for the meal planning agent."""
        try:
            # Validate environment
            settings.validate_settings()
            
            # Step 1: Collect user preferences
            self.user_preferences = await self._collect_user_preferences()
            
            # Step 2: Search for recipes
            await self.send_message("Searching for recipes that match your preferences...")
            recipes = await self._search_recipes()
            
            # Step 3: Let user select recipes
            await self.send_message("Finding the best recipe matches...")
            selected_recipes = await self._get_recipe_selections(recipes)
            
            # Step 4: Generate shopping list
            await self.send_message("Generating your shopping list...")
            shopping_list = await self._generate_shopping_list(selected_recipes)
            
            # Present results to user
            await self._present_results(selected_recipes, shopping_list)
            
        except Exception as e:
            await self.send_message(f"An error occurred: {str(e)}", "error")
            raise
    
    async def _collect_user_preferences(self) -> UserPreferences:
        """Collect and validate user preferences through natural conversation."""
        messages = [
            {"role": "system", "content": """You are a helpful meal planning assistant. 
             Your task is to collect the following information in a friendly, conversational way:
             1. Number of meals they need for the week
             2. Cuisine preferences (Italian, Mexican, Asian, etc.)
             3. Any dietary restrictions (vegetarian, vegan, gluten-free, etc.)
             4. Days they're available to cook
             5. Number of servings per meal
             
             Start by welcoming them and asking about the number of meals.
             Be friendly and conversational while efficiently collecting information.
             After collecting all information, summarize it and ask for confirmation.
             When the user confirms, respond ONLY with: "Great! Let me search for recipes that match your preferences..."
             """},
            {"role": "assistant", "content": "Hi! I'm here to help you plan your meals for the week. Let's start with how many meals you'd like to prepare. How many dinners would you like to plan?"}
        ]
        
        # Initialize preferences with default values
        preferences = None
        
        # Send the first message
        await self.send_message(messages[1]["content"])
        
        while preferences is None:
            # Get user's response
            user_response = await self.get_user_input()
            
            # Add user's response to messages
            messages.append({"role": "user", "content": user_response})
            
            # Get next message from OpenAI
            response = await self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                temperature=0.7
            )
            
            # Send assistant's message
            assistant_message = response.choices[0].message.content
            await self.send_message(assistant_message)
            
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
                     6. Use exact field names as shown"""},
                    {"role": "user", "content": str(messages[:-2])}  # Exclude the last confirmation exchange
                ]
                
                try:
                    extraction_response = await self.client.chat.completions.create(
                        model=settings.MODEL_NAME,
                        messages=extraction_messages,
                        temperature=0
                    )
                    
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
                            await self.send_message("\nI apologize, but I couldn't properly capture all your preferences. Let's try again.")
                            preferences = None
                    else:
                        await self.send_message("\nI apologize, but I couldn't properly extract your preferences. Let's try again.")
                        preferences = None
                except json.JSONDecodeError as e:
                    await self.send_message(f"\nError parsing preferences: {str(e)}")
                    preferences = None
                except Exception as e:
                    await self.send_message(f"\nUnexpected error while extracting preferences: {str(e)}")
                    preferences = None
                break  # Exit the loop if we got the transition message
            
            # Add assistant's message to conversation
            messages.append({"role": "assistant", "content": assistant_message})
        
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
    
    async def _extract_preferences(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
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
        
        response = await self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=extraction_messages,
            temperature=0
        )
        
        # Parse the response as JSON
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
        all_recipes = []
        
        # If no cuisine preferences, do a single search with default query
        if not self.user_preferences.cuisine_preferences:
            return self.recipe_api.search_recipes(
                query="healthy",  # Default query if no cuisine preferences
                diet=self.user_preferences.dietary_restrictions,
                meal_type=["lunch/dinner"],
                dish_type=["main course"]
            )
        
        # Search for each cuisine type separately
        for cuisine in self.user_preferences.cuisine_preferences:
            await self.send_message(f"\nSearching for {cuisine} recipes...")
            cuisine_recipes = self.recipe_api.search_recipes(
                query=cuisine,  # Use cuisine type as the query
                diet=self.user_preferences.dietary_restrictions,
                cuisine_type=[cuisine],  # Search for this specific cuisine
                meal_type=["lunch/dinner"],
                dish_type=["main course"],
                max_results=5  # Limit results per cuisine to ensure variety
            )
            all_recipes.extend(cuisine_recipes)
        
        # Shuffle the combined results to mix cuisines
        import random
        random.shuffle(all_recipes)
        
        # Return the combined results, limited to a reasonable number
        return all_recipes[:10]  # Limit total results to 10 recipes
    
    async def _get_recipe_selections(self, recipes: List[Recipe]) -> List[Recipe]:
        """Present recipes to user and get their selections."""
        if not recipes:
            await self.send_message("\nNo recipes found matching your criteria. Please try again with different preferences.")
            return []

        # Calculate how many recipes we need based on cooking days
        needed_recipes = len(self.user_preferences.cooking_days)
        
        # Keep track of all recipes shown
        all_recipes = recipes.copy()
        current_recipes = recipes
        
        async def display_current_recipes():
            await self.send_message("\nAvailable recipes:")
            for i, recipe in enumerate(current_recipes, 1):
                servings_info = f"(Can be adjusted to {self.user_preferences.servings_per_meal} servings)"
                cooking_time = f", {recipe.total_time} minutes" if recipe.total_time else ""
                await self.send_message(f"\n{i}. {recipe.name} {servings_info}{cooking_time}")
                await self.send_message(f"   Cuisine: {', '.join(recipe.cuisine_type) if recipe.cuisine_type else 'Not specified'}")
                await self.send_message(f"   Link: {recipe.url}")

        await display_current_recipes()
        selected_indices = set()
        
        # Send initial selection prompt
        await self.send_message(f"""I see you need {needed_recipes} recipes for your cooking days: {', '.join(self.user_preferences.cooking_days)}.
        
You can:
- Select recipes by their numbers or names
- Ask to see more recipes with specific criteria

For example:
- "I'd like the pasta recipe and the chicken curry"
- "Number 2 and 4 look good"
- "Show me more chicken recipes"

Which {needed_recipes} recipes would you like?""")
        
        while len(selected_indices) != needed_recipes:
            # Get user's response
            user_response = await self.get_user_input()
            
            try:
                # Create a context message with recipe information
                recipe_context = "Available recipes:\n" + "\n".join(
                    f"{i}. {recipe.name}" for i, recipe in enumerate(current_recipes, 1)
                )
                
                # Ask OpenAI to parse the response
                extraction_messages = [
                    {"role": "system", "content": f"""Determine if the user is selecting recipes or requesting more recipes.
                     {recipe_context}
                     
                     If selecting recipes:
                     Return ONLY a JSON array of integers representing the selected recipe indices.
                     
                     If requesting more recipes:
                     Return ONLY "MORE_RECIPES: <search_term>"
                     
                     If unclear:
                     Return "[]"
                     
                     Examples:
                     [1, 3]
                     "MORE_RECIPES: chicken"
                     []"""},
                    {"role": "user", "content": user_response}
                ]
                
                response = await self.client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=extraction_messages,
                    temperature=0
                )
                
                result = response.choices[0].message.content.strip()
                
                # Check if user is requesting more recipes
                if result.startswith("MORE_RECIPES:"):
                    search_term = result.split(":", 1)[1].strip()
                    await self.send_message(f"\nSearching for more recipes with '{search_term}'...")
                    
                    # Search for additional recipes
                    new_recipes = self.recipe_api.search_recipes(
                        query=search_term,
                        diet=self.user_preferences.dietary_restrictions,
                        meal_type=["lunch/dinner"],
                        dish_type=["main course"]
                    )
                    
                    # Filter out recipes we've already shown
                    seen_urls = {recipe.url for recipe in all_recipes}
                    new_recipes = [r for r in new_recipes if r.url not in seen_urls]
                    
                    if new_recipes:
                        # Update recipe lists
                        current_recipes = new_recipes
                        all_recipes.extend(new_recipes)
                        await display_current_recipes()
                        
                        await self.send_message("Here are some additional recipes. Which would you like to select?")
                    else:
                        await self.send_message("I couldn't find any new recipes matching your criteria. Please select from the current options or try a different search.")
                    continue
                
                # Handle recipe selection
                import json
                if result.startswith("["):
                    new_indices = set(json.loads(result))
                else:
                    new_indices = set()
                
                # Validate indices
                valid_indices = {i for i in new_indices if 1 <= i <= len(current_recipes)}
                
                if not valid_indices:
                    await self.send_message(f"""I'm not sure which recipes you want. You can:
                     - Select recipes by number or name
                     - Ask to see more recipes with specific criteria
                     
                     Please select {needed_recipes} recipes or ask for more options.""")
                    continue
                
                # Update selected indices
                selected_indices = valid_indices
                
                # Check if we have the right number of recipes
                if len(selected_indices) < needed_recipes:
                    remaining = needed_recipes - len(selected_indices)
                    await self.send_message(f"""I understood you want: {', '.join(current_recipes[i-1].name for i in selected_indices)}.
                     You still need to select {remaining} more recipe(s).
                     You can:
                     - Select from the current recipes
                     - Ask to see more recipes with specific criteria""")
                elif len(selected_indices) > needed_recipes:
                    await self.send_message(f"""I understood you want: {', '.join(current_recipes[i-1].name for i in selected_indices)}.
                     However, you only need {needed_recipes} recipes.
                     Please select exactly {needed_recipes} recipes.""")
                else:
                    await self.send_message(f"""Perfect! You've selected:
                     {chr(10).join(f'- {current_recipes[i-1].name}' for i in selected_indices)}""")
                    
            except Exception as e:
                await self.send_message(f"\nError parsing selection: {e}")
                await self.send_message(f"""I didn't understand that. You can:
                     - Select recipes by number (1-{len(current_recipes)})
                     - Select recipes by name
                     - Ask to see more recipes with specific criteria
                     
                     Please select {needed_recipes} recipes or ask for more options.""")

        # Return selected recipes from the current set
        return [current_recipes[i-1] for i in selected_indices]
    
    async def _generate_shopping_list(self, recipes: List[Recipe]) -> List[Dict[str, str]]:
        """Generate consolidated shopping list from selected recipes."""
        self.shopping_list.clear()
        
        # Calculate total servings needed for the week
        total_servings_needed = len(self.user_preferences.cooking_days) * self.user_preferences.servings_per_meal
        
        # Get optimal distribution of servings
        multipliers = calculate_optimal_servings_distribution(recipes, total_servings_needed)
        
        # Add each recipe with its optimal multiplier
        for recipe, multiplier in zip(recipes, multipliers):
            self.shopping_list.add_recipe(recipe, servings_multiplier=multiplier)
        
        return self.shopping_list.get_consolidated_list()
    
    async def _present_results(self, recipes: List[Recipe], shopping_list: List[Dict[str, str]]):
        """Present the final meal plan and shopping list to the user."""
        # Calculate total servings needed and actual servings
        total_servings_needed = len(self.user_preferences.cooking_days) * self.user_preferences.servings_per_meal
        multipliers = calculate_optimal_servings_distribution(recipes, total_servings_needed)
        
        # Format and send meal plan
        meal_plan = "\n=== Your Weekly Dinner Plan ===\n\n"
        
        # Map recipes to days
        available_days = self.user_preferences.cooking_days
        recipes_by_day = {}
        
        for day, recipe, multiplier in zip(available_days, recipes, multipliers):
            recipes_by_day[day] = (recipe, multiplier)
        
        # Format recipes by day
        for day in available_days:
            meal_plan += f"\n{day}:\n"
            if day in recipes_by_day:
                recipe, multiplier = recipes_by_day[day]
                scaled_servings = int(recipe.servings * multiplier)
                meal_plan += self._format_recipe_details(recipe, scaled_servings)
            else:
                meal_plan += "  • No recipe planned\n"
        
        await self.send_message(meal_plan)
        
        # Format and send shopping list
        shopping_list_text = "\n=== Shopping List ===\n"
        
        # Group items by category
        categorized_items = {}
        for item in shopping_list:
            category = item.get("category", "Other")
            if category not in categorized_items:
                categorized_items[category] = []
            categorized_items[category].append(item)
        
        # Format items by category
        for category, items in sorted(categorized_items.items()):
            shopping_list_text += f"\n{category}:\n"
            for item in items:
                quantity = item.get("quantity", "")
                measure = item.get("measure", "")
                food = item.get("food", "")
                shopping_list_text += f"  • {quantity} {measure} {food}\n".strip() + "\n"
        
        await self.send_message(shopping_list_text)
        
        # Send summary
        summary = f"\nSummary:\n"
        summary += f"• Planned dinners: {len(recipes)}\n"
        summary += f"• Cooking days: {', '.join(available_days)}\n"
        summary += f"• Servings per meal: {self.user_preferences.servings_per_meal}\n"
        if self.user_preferences.dietary_restrictions:
            summary += f"• Dietary restrictions: {', '.join(self.user_preferences.dietary_restrictions)}\n"
        
        summary += "\nEnjoy your meals! 🍽️"
        await self.send_message(summary)
    
    def _format_recipe_details(self, recipe: Recipe, scaled_servings: Optional[int] = None) -> str:
        """Format recipe details as a string."""
        details = []
        details.append(f"  • {recipe.name}")
        
        if scaled_servings:
            details.append(f"    Servings: {scaled_servings} (scaled from original {recipe.servings})")
        else:
            details.append(f"    Servings: {recipe.servings}")
        
        if recipe.total_time:
            details.append(f"    Time: {recipe.total_time} minutes")
        
        if recipe.cuisine_type:
            details.append(f"    Cuisine: {', '.join(recipe.cuisine_type)}")
        
        if recipe.diet_labels:
            details.append(f"    Diet Labels: {', '.join(recipe.diet_labels)}")
        if recipe.health_labels:
            details.append(f"    Health Labels: {', '.join(recipe.health_labels[:3])}")
        
        if recipe.calories:
            calories_per_serving = recipe.calories / recipe.servings
            if scaled_servings:
                details.append(f"    Calories per serving: {int(calories_per_serving)} kcal (total: {int(calories_per_serving * scaled_servings)} kcal)")
            else:
                details.append(f"    Calories per serving: {int(calories_per_serving)} kcal")
        
        details.append(f"    Recipe Link: {recipe.url}")
        return "\n".join(details) + "\n"

if __name__ == "__main__":
    import asyncio
    
    agent = MealPlannerAgent()
    asyncio.run(agent.run()) 