"""Configuration management for the PromoPack Claim Extractor."""

import importlib
import os
from typing import Any, Dict


class Config:
    """Application configuration with environment-specific loading."""

    # Default attributes (will be overridden by env config)
    env: str = "dev"
    api_key_secret: str = ""
    langextract_api_key: str = ""
    log_to_file: bool = False
    log_level: str = "INFO"
    rate_limit_requests: int = 10
    rate_limit_window: int = 60
    max_file_size: int = 20 * 1024 * 1024
    max_pages: int = 1000
    request_timeout: float = 30.0
    service_name: str = "promopack-extractor"
    version: str = "1.0"
    database_url: str = ""
    redis_url: str = ""
    use_secrets_manager: bool = False
    secrets_manager_url: str = ""

    def __init__(self):
        # Determine environment
        self.env = os.getenv("ENV", "dev").lower()

        # Load environment-specific configuration
        self._load_env_config()

        # Validate configuration
        self._validate_config()

    def _load_env_config(self):
        """Load configuration from environment-specific module."""
        try:
            env_module = importlib.import_module(f"config.{self.env}")
        except ImportError:
            raise ValueError(f"Configuration for environment '{self.env}' not found. "
                           f"Create config/{self.env}.py")

        # Copy all attributes from the env module
        for attr in dir(env_module):
            if not attr.startswith('_'):
                value = getattr(env_module, attr)
                setattr(self, attr, value)

    def _validate_config(self):
        """Validate that required configuration is present."""
        required_attrs = ['api_key_secret', 'langextract_api_key']
        missing = []

        for attr in required_attrs:
            if not getattr(self, attr, None):
                missing.append(attr)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        # Validate numeric values
        if hasattr(self, 'rate_limit_requests') and self.rate_limit_requests <= 0:
            raise ValueError("rate_limit_requests must be positive")

        if hasattr(self, 'max_file_size') and self.max_file_size <= 0:
            raise ValueError("max_file_size must be positive")

    def is_ready(self) -> bool:
        """Check if the service is ready to handle requests."""
        return bool(getattr(self, 'api_key_secret', None) and
                   getattr(self, 'langextract_api_key', None))

    def get_secrets_manager_config(self) -> Dict[str, Any]:
        """Get secrets manager configuration."""
        return {
            'enabled': getattr(self, 'use_secrets_manager', False),
            'url': getattr(self, 'secrets_manager_url', ''),
        }

    def reload(self):
        """Reload configuration (for hot-reloading)."""
        self._load_env_config()
        self._validate_config()


# Global config instance
config = Config()