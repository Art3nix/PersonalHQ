"""App configuration module."""

import os

from .base import Config

class DockerTestingConfig(Config): # pylint: disable=R0903; # flask config class used to only store data
    """Class representing app testing configuration for testing in Docker container."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DOCKER_TEST_DATABASE_URL")
    WTF_CSRF_ENABLED = False  # useful for testing forms


class LocalTestingConfig(Config): # pylint: disable=R0903; # flask config class used to only store data
    """Class representing app testing configuration for testing using virtual env."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("LOCAL_TEST_DATABASE_URL")
    WTF_CSRF_ENABLED = False  # useful for testing forms
