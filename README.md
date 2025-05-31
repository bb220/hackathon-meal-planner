# AI Meal Planner

An intelligent meal planning assistant that helps you plan your weekly meals and generate shopping lists.

## Features

- Interactive chat-based interface using OpenAI's Agent SDK
- Collects user preferences for meals, dietary restrictions, and cooking availability
- Integrates with Edamam Recipe API for recipe suggestions
- Generates consolidated shopping lists
- Handles recipe scaling based on needed meal portions

## Setup

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   EDAMAM_APP_ID=your_edamam_app_id
   EDAMAM_APP_KEY=your_edamam_app_key
   ```

## Project Structure

- `agent.py` - Main agent implementation
- `config.py` - Configuration and environment variable management
- `tools/` - Custom tools and utilities
  - `user_input.py` - User input collection tools
  - `recipe.py` - Recipe API integration
  - `shopping_list.py` - Shopping list generation utilities

## Usage

Run the meal planner:
```bash
python agent.py
```

Follow the interactive prompts to:
1. Specify your dietary preferences and restrictions
2. Indicate how many meals you need
3. Choose your preferred cuisines
4. Select from suggested recipes
5. Get your consolidated shopping list 