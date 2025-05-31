from typing import List, Dict, Optional, Union
import requests
from pydantic import BaseModel, Field
from config import settings

class Measure(BaseModel):
    """Model for ingredient measures."""
    uri: str
    label: str
    weight: float

class Food(BaseModel):
    """Model for food items."""
    foodId: str
    label: str
    
class Ingredient(BaseModel):
    """Model for recipe ingredients based on Edamam API spec."""
    foodId: Optional[str] = None
    quantity: str  # Store as string to handle both integers and decimals
    measure: Optional[str] = Field(default="unit")
    weight: Optional[float] = None
    food: str
    foodCategory: Optional[str] = None

class RecipeImage(BaseModel):
    """Model for recipe images."""
    url: str
    width: int
    height: int

class RecipeImages(BaseModel):
    """Model for different recipe image sizes."""
    THUMBNAIL: Optional[RecipeImage] = None
    SMALL: Optional[RecipeImage] = None
    REGULAR: Optional[RecipeImage] = None
    LARGE: Optional[RecipeImage] = None

class Recipe(BaseModel):
    """Model for recipe data based on Edamam API spec."""
    id: str
    name: str
    url: str
    image: Optional[str]
    images: Optional[RecipeImages] = None
    cuisine_type: List[str] = Field(default_factory=list)
    meal_type: List[str] = Field(default_factory=list)
    dish_type: List[str] = Field(default_factory=list)
    diet_labels: List[str] = Field(default_factory=list)
    health_labels: List[str] = Field(default_factory=list)
    ingredients: List[Ingredient]
    servings: int
    total_time: Optional[int] = None  # in minutes
    calories: Optional[float] = None
    total_nutrients: Optional[Dict[str, Dict[str, Union[str, float]]]] = None
    total_daily: Optional[Dict[str, Dict[str, Union[str, float]]]] = None
    co2_emissions_class: Optional[str] = None

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
        health: Optional[List[str]] = None,
        cuisine_type: Optional[List[str]] = None,
        meal_type: Optional[List[str]] = None,
        dish_type: Optional[List[str]] = None,
        image_size: Optional[str] = None,
        max_results: int = 10
    ) -> List[Recipe]:
        """
        Search for recipes matching the given criteria.
        
        Args:
            query: Search query string
            diet: List of dietary restrictions (e.g., balanced, high-protein)
            health: List of health labels (e.g., vegan, vegetarian)
            cuisine_type: List of cuisine types
            meal_type: List of meal types (e.g., breakfast, lunch)
            dish_type: List of dish types (e.g., main course, dessert)
            image_size: Required image size (THUMBNAIL, SMALL, REGULAR, LARGE)
            max_results: Maximum number of results to return
            
        Returns:
            List of Recipe objects
        """
        params = {
            "type": "public",
            "app_id": self.app_id,
            "app_key": self.app_key,
            "q": query,
            "beta": "true"  # Enable CO2 emissions data
        }
        
        if diet:
            params["diet"] = diet
        if health:
            params["health"] = health
        if cuisine_type:
            params["cuisineType"] = cuisine_type
        if meal_type:
            params["mealType"] = meal_type
        if dish_type:
            params["dishType"] = dish_type
        if image_size:
            params["imageSize"] = image_size.upper()
            
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
                    images=RecipeImages(**recipe.get("images", {})) if recipe.get("images") else None,
                    cuisine_type=recipe.get("cuisineType", []),
                    meal_type=recipe.get("mealType", []),
                    dish_type=recipe.get("dishType", []),
                    diet_labels=recipe.get("dietLabels", []),
                    health_labels=recipe.get("healthLabels", []),
                    ingredients=[
                        Ingredient(
                            foodId=ing.get("foodId"),
                            food=ing["food"],
                            quantity=str(ing["quantity"]),
                            measure=ing.get("measure") or "unit",
                            weight=ing.get("weight"),
                            foodCategory=ing.get("foodCategory")
                        )
                        for ing in recipe["ingredients"]
                    ],
                    servings=recipe["yield"],
                    total_time=recipe.get("totalTime"),
                    calories=recipe.get("calories"),
                    total_nutrients=recipe.get("totalNutrients"),
                    total_daily=recipe.get("totalDaily"),
                    co2_emissions_class=recipe.get("co2EmissionsClass")
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
            "uri": f"http://www.edamam.com/ontologies/edamam.owl#recipe_{recipe_id}",
            "beta": "true"  # Enable CO2 emissions data
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
            images=RecipeImages(**recipe_data.get("images", {})) if recipe_data.get("images") else None,
            cuisine_type=recipe_data.get("cuisineType", []),
            meal_type=recipe_data.get("mealType", []),
            dish_type=recipe_data.get("dishType", []),
            diet_labels=recipe_data.get("dietLabels", []),
            health_labels=recipe_data.get("healthLabels", []),
            ingredients=[
                Ingredient(
                    foodId=ing.get("foodId"),
                    food=ing["food"],
                    quantity=str(ing["quantity"]),
                    measure=ing.get("measure") or "unit",
                    weight=ing.get("weight"),
                    foodCategory=ing.get("foodCategory")
                )
                for ing in recipe_data["ingredients"]
            ],
            servings=recipe_data["yield"],
            total_time=recipe_data.get("totalTime"),
            calories=recipe_data.get("calories"),
            total_nutrients=recipe_data.get("totalNutrients"),
            total_daily=recipe_data.get("totalDaily"),
            co2_emissions_class=recipe_data.get("co2EmissionsClass")
        ) 