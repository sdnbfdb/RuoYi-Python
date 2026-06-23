"""
Application configuration module.
Centralized configuration management for the Flask application.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Base configuration class."""
    
    # Application settings
    APP_NAME = "RuoYi-Python"
    DEBUG = False
    TESTING = False
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080').split(',')
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
    CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_MAX_AGE = 3600
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent
    IMAGE_DIR = BASE_DIR / 'image'
    DATA_DIR = BASE_DIR / 'data'
    UPLOAD_DIR = BASE_DIR / 'uploads'
    KNOWLEDGE_DIR = DATA_DIR / 'knowledge'
    
    # API Keys (loaded from environment)
    API_KEY: Optional[str] = os.getenv('API_KEY')
    SEARCH_API_KEY: Optional[str] = os.getenv('SEARCH_API_KEY')
    SEARCH_API_ID: Optional[str] = os.getenv('SEARCH_API_ID')
    
    # API URLs
    DASHSCOPE_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    
    # Model settings
    DEFAULT_CHAT_MODEL = 'qwen-turbo'
    DEFAULT_VISION_MODEL = 'qwen-vl-plus'
    
    # Database (if using)
    # DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///ruoyi.db')
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        for directory in [cls.IMAGE_DIR, cls.DATA_DIR, cls.UPLOAD_DIR, cls.KNOWLEDGE_DIR]:
            directory.mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    CORS_ORIGINS = ["*"]  # Allow all origins in development


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Override with production-specific settings
    

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """Get configuration based on environment.
    
    Args:
        env: Environment name ('development', 'production', 'testing')
        
    Returns:
        Configuration class instance
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])
