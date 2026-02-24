"""App configuration module."""

import os

from .base import Config

class ProductionConfig(Config): # pylint: disable=R0903; # flask config class used to only store data
    """Production configuration."""

    # If SECRET_KEY is default, crash early
    if os.environ.get("SECRET_KEY") is None:
        raise RuntimeError("SECRET_KEY environment variable is required in production.")

    # If DB URL is missing, crash early
    if os.environ.get("DATABASE_URL") is None:
        raise RuntimeError("DATABASE_URL environment variable is required in production.")

    # Stricter security for prod
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"
