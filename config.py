import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EDAMAM_APP_ID: str = os.getenv("EDAMAM_APP_ID", "")
    EDAMAM_APP_KEY: str = os.getenv("EDAMAM_APP_KEY", "")
    EDAMAM_USER_ID: str = os.getenv("EDAMAM_USER_ID", "")
    
    # Edamam API endpoints
    EDAMAM_BASE_URL: str = "https://api.edamam.com/api/recipes/v2"
    
    # OpenAI settings
    MODEL_NAME: str = "gpt-4-turbo-preview"
    
    def validate_settings(self) -> None:
        """Validate that all required settings are set."""
        missing = []
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.EDAMAM_APP_ID:
            missing.append("EDAMAM_APP_ID")
        if not self.EDAMAM_APP_KEY:
            missing.append("EDAMAM_APP_KEY")
        if not self.EDAMAM_USER_ID:
            missing.append("EDAMAM_USER_ID")
            
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Create global settings instance
settings = Settings() 