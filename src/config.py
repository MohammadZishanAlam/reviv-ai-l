import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Reviv-AI-l"
    VERSION: str = "1.0.0"
    TRACK: str = "Razorpay AI Buildathon 2026 - Track 3 (AI Revenue Recovery)"
    
    # Razorpay Credentials
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_placeholder")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "placeholder_secret")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "webhook_secret_placeholder")
    
    # AI Engine
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # App Settings
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'reviv_ail.db'}"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    @property
    def is_razorpay_live(self) -> bool:
        """Returns True if real Razorpay test/live keys are provided."""
        return (
            bool(self.RAZORPAY_KEY_ID) 
            and self.RAZORPAY_KEY_ID.startswith("rzp_") 
            and "your_key" not in self.RAZORPAY_KEY_ID
            and "placeholder" not in self.RAZORPAY_KEY_ID
            and bool(self.RAZORPAY_KEY_SECRET)
            and "your_key" not in self.RAZORPAY_KEY_SECRET
            and "placeholder" not in self.RAZORPAY_KEY_SECRET
        )

    @property
    def is_gemini_live(self) -> bool:
        """Returns True if a real Gemini API key is provided."""
        return (
            bool(self.GEMINI_API_KEY) 
            and len(self.GEMINI_API_KEY) > 15
            and "your_gemini_api_key" not in self.GEMINI_API_KEY
            and "placeholder" not in self.GEMINI_API_KEY
        )

settings = Settings()
