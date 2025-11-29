"""
Configuration Management - Bill Extraction API
Loads settings from environment variables with validation
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # ========== Grok API Configuration ==========
    GROK_API_KEY = os.getenv("GROK_API_KEY")
    GROK_MODEL = os.getenv("GROK_MODEL", "llama-3.1-8b-instant")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    
    # ========== Flask Configuration ==========
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", "3000"))
    
    # ========== OCR Configuration ==========
    OCR_SERVICE = os.getenv("OCR_SERVICE", "tesseract")
    TESSERACT_CMD = os.getenv("TESSERACT_CMD", None)
    
    # ========== Logging Configuration ==========
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # ========== Request Settings ==========
    REQUEST_TIMEOUT = 120  # seconds
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_OCR_CHARS = 8000  # Max OCR chars per API call
    
    # ========== Validation Settings ==========
    MIN_CONFIDENCE_SCORE = 0.7
    VARIANCE_THRESHOLD_PCT = 5.0  # Variance threshold percentage
    
    # ========== Response Settings ==========
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    @staticmethod
    def validate_config() -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not Config.GROK_API_KEY:
            raise ValueError(
                "❌ GROK_API_KEY not set. Add to .env:\n"
                "GROK_API_KEY=gsk_your_key_here"
            )
        
        if not Config.GROK_API_KEY.startswith("gsk_"):
            raise ValueError(
                "⚠️  GROK_API_KEY format invalid. Should start with 'gsk_'"
            )
        
        return True
    
    @staticmethod
    def get_config_summary() -> dict:
        """Get configuration summary without sensitive data"""
        return {
            "environment": Config.ENVIRONMENT,
            "debug": Config.DEBUG,
            "port": Config.PORT,
            "grok_model": Config.GROK_MODEL,
            "ocr_service": Config.OCR_SERVICE,
            "log_level": Config.LOG_LEVEL,
            "api_key_set": bool(Config.GROK_API_KEY),
        }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    REQUEST_TIMEOUT = 120


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    REQUEST_TIMEOUT = 60


def get_config(env: str = None) -> Config:
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv("ENVIRONMENT", "development")
    
    configs = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    
    return configs.get(env.lower(), DevelopmentConfig)()


if __name__ == "__main__":
    print("🔍 Validating Configuration...")
    print("-" * 60)
    
    try:
        Config.validate_config()
        print("✅ Configuration validation PASSED!\n")
        print("📊 Current Configuration:")
        print("-" * 60)
        for key, value in Config.get_config_summary().items():
            if key == "api_key_set":
                print(f"  {key:25s}: {'✅ Set' if value else '❌ Not set'}")
            else:
                print(f"  {key:25s}: {value}")
        print("-" * 60)
    except ValueError as e:
        print(f"❌ {e}")
        exit(1)