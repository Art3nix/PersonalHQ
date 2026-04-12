"""Development configuration module."""

import os

from .base import Config

class DevelopmentConfig(Config): # pylint: disable=R0903; # flask config class used to only store data
    """Local development configuration."""

    # Local dev DB if not overridden
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL")
