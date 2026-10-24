"""
Centralized configuration for the Athletic Performance Tracker.
Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5433")
    DB_NAME = os.getenv("DB_NAME", "athletic_tracker")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

    # Flask
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-fallback-secret-key")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    @classmethod
    def get_dsn(cls):
        """Return a psycopg2-compatible DSN string."""
        return (
            f"host={cls.DB_HOST} port={cls.DB_PORT} "
            f"dbname={cls.DB_NAME} user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD}"
        )
