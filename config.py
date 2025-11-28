"""
Configuration management for Bill Extraction API
Handles environment variables and application settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration class
    Loads all settings from environment variables
    """
    
    # ========== Anthropic API Configuration ==========
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
    
    # ========== Flask Configuration ==========
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", "3000"))
    
    # ========== OCR Configuration ==========
    OCR_SERVICE = os.getenv("OCR_SERVICE", "google_vision")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", None)
    
    # ========== Logging Configuration ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # ========== Request Settings ==========
    REQUEST_TIMEOUT = 60  # seconds
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # ========== Validation Settings ==========
    MIN_CONFIDENCE_SCORE = 0.7
    
    # ========== Response Settings ==========
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    @staticmethod
    def validate_config() -> bool:
        """
        Validate that all required configuration is present
        
        Returns:
            True if all required config is valid
            
        Raises:
            ValueError: If required config is missing
        """
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError(
                "❌ ANTHROPIC_API_KEY environment variable not set. "
                "Please add it to .env file or set it as environment variable."
            )
        
        if not Config.ANTHROPIC_API_KEY.startswith("sk-ant-"):
            raise ValueError(
                "⚠️  ANTHROPIC_API_KEY format seems invalid. "
                "It should start with 'sk-ant-'"
            )
        
        return True
    
    @staticmethod
    def get_config_summary() -> dict:
        """
        Get a summary of current configuration (without sensitive data)
        
        Returns:
            Dictionary with configuration summary
        """
        return {
            "environment": Config.ENVIRONMENT,
            "debug": Config.DEBUG,
            "port": Config.PORT,
            "flask_env": Config.FLASK_ENV,
            "ocr_service": Config.OCR_SERVICE,
            "claude_model": Config.CLAUDE_MODEL,
            "max_tokens": Config.MAX_TOKENS,
            "log_level": Config.LOG_LEVEL,
            "api_key_set": bool(Config.ANTHROPIC_API_KEY),
        }


# ============================================================================
# Environment-specific configurations (optional for future use)
# ============================================================================

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    REQUEST_TIMEOUT = 90


class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = True
    TESTING = True
    REQUEST_TIMEOUT = 30


# ============================================================================
# Configuration selector
# ============================================================================

def get_config(env: str = None) -> Config:
    """
    Get configuration based on environment
    
    Args:
        env: Environment name (development, production, testing)
        
    Returns:
        Configuration object for the specified environment
    """
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    config_class = configs.get(env.lower(), DevelopmentConfig)
    return config_class()


if __name__ == "__main__":
    # Quick validation script
    print("🔍 Validating Configuration...")
    print("-" * 50)
    
    try:
        Config.validate_config()
        print("✅ Configuration validation passed!")
        print("\n📊 Current Configuration:")
        print("-" * 50)
        summary = Config.get_config_summary()
        for key, value in summary.items():
            print(f"  {key:20s}: {value}")
        print("-" * 50)
    except ValueError as e:
        print(f"❌ {e}")
        exit(1)