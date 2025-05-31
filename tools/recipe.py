from typing import List, Dict, Optional
import requests
from pydantic import BaseModel
from config import settings

class Recipe(BaseModel):
    """Model for recipe data."""
    id: str
    name: str
    url: str
    image: Optional[str]
    cuisine_type: List[str]
    ingredients: List[Dict[str, str]]  # List of ingredients with quantities
    servings: int
    total_time: Optional[int]  # in minutes

class RecipeAPI:
    """Client for interacting with Edamam Recipe API."""
    
    def __init__(self):
        self.base_url = settings.EDAMAM_BASE_URL
        self.app_id = settings.EDAMAM_APP_ID
        self.app_key = settings.EDAMAM_APP_KEY
        self.user_id = settings.EDAMAM_USER_ID
        self.headers = {
            "Edamam-Account-User": self.user_id
        }

    def search_recipes(
        self,
        query: str,
        diet: Optional[List[str]] = None,
        cuisine_type: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[Recipe]:
        """
        Search for recipes matching the given criteria.
        
        Args:
            query: Search query string
            diet: List of dietary restrictions
            cuisine_type: List of cuisine types
            max_results: Maximum number of results to return
            
        Returns:
            List of Recipe objects
        """
        params = {
            "type": "public",
            "app_id": self.app_id,
            "app_key": self.app_key,
            "q": query,
        }
        
        if diet:
            params["health"] = diet
        if cuisine_type:
            params["cuisineType"] = cuisine_type
            
        response = requests.get(self.base_url, params=params, headers=self.headers)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error Status Code: {response.status_code}")
            print(f"Error Response Headers: {response.headers}")
            print(f"Error Response Body: {response.text}")
            raise
        
        recipes = []
        for hit in response.json().get("hits", [])[:max_results]:
            recipe = hit["recipe"]
            recipes.append(
                Recipe(
                    id=recipe["uri"].split("#")[-1],
                    name=recipe["label"],
                    url=recipe["url"],
                    image=recipe.get("image"),
                    cuisine_type=recipe.get("cuisineType", []),
                    ingredients=[
                        {
                            "food": ing["food"],
                            "quantity": ing["quantity"],
                            "measure": ing.get("measure", "unit")
                        }
                        for ing in recipe["ingredients"]
                    ],
                    servings=recipe["yield"],
                    total_time=recipe.get("totalTime")
                )
            )
        
        return recipes

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Recipe]:
        """
        Fetch a specific recipe by its ID.
        
        Args:
            recipe_id: The recipe ID
            
        Returns:
            Recipe object if found, None otherwise
        """
        params = {
            "type": "public",
            "app_id": self.app_id,
            "app_key": self.app_key,
            "uri": f"http://www.edamam.com/ontologies/edamam.owl#recipe_{recipe_id}"
        }
        
        response = requests.get(self.base_url, params=params, headers=self.headers)
        try:
            if response.status_code == 404:
                return None
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error Status Code: {response.status_code}")
            print(f"Error Response Headers: {response.headers}")
            print(f"Error Response Body: {response.text}")
            raise
            
        recipe_data = response.json()["hits"][0]["recipe"]
        
        return Recipe(
            id=recipe_id,
            name=recipe_data["label"],
            url=recipe_data["url"],
            image=recipe_data.get("image"),
            cuisine_type=recipe_data.get("cuisineType", []),
            ingredients=[
                {
                    "food": ing["food"],
                    "quantity": ing["quantity"],
                    "measure": ing.get("measure", "unit")
                }
                for ing in recipe_data["ingredients"]
            ],
            servings=recipe_data["yield"],
            total_time=recipe_data.get("totalTime")
        ) 