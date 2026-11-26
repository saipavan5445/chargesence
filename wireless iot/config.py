"""
ChargeSense Configuration Module
Handles environment variables, database connection strings, security keys,
and simulation settings.
"""

import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'chargesense-dev-secret-key-default-2026')
    
    # Database configuration
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'chargesense_db')
    
    # Priority: explicit DATABASE_URL in .env, otherwise build MySQL URI
    database_url_env = os.getenv('DATABASE_URL')
    if database_url_env:
        SQLALCHEMY_DATABASE_URI = database_url_env
    else:
        # Standard MySQL connection via PyMySQL
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security Settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ChargeSense Default Simulation Constants
    DEFAULT_TARGET_PERCENTAGE = 80
    DEFAULT_CHARGING_SPEED = 'normal'  # slow, normal, fast
    
    # Simulation rates in battery % per minute
    CHARGING_RATES = {
        'slow': 0.5,    # 0.5% per minute (~5W trickle / USB)
        'normal': 1.0,  # 1.0% per minute (~15-18W standard)
        'fast': 2.5,    # 2.5% per minute (~30W+ fast charging)
        'turbo': 6.0    # 6.0% per minute (~65W+ ultra fast demo)
    }
    
    # Telemetry simulation update interval (seconds in real-time)
    TELEMETRY_INTERVAL_SECONDS = 3

    # Twilio SMS API Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
