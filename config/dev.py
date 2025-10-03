"""Development configuration."""

import os

# Environment
ENV = "dev"

# API settings
api_key_secret = os.getenv("API_KEY_SECRET", "dev-secret-key")
langextract_api_key = os.getenv("LANGEXTRACT_API_KEY", "")

# Logging settings
log_to_file = os.getenv("LOG_TO_FILE", "false").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "DEBUG")

# Rate limiting (more permissive for dev)
rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# File processing limits (smaller for dev)
max_file_size = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10MB
max_pages = int(os.getenv("MAX_PAGES", "500"))

# HTTP client settings
request_timeout = float(os.getenv("REQUEST_TIMEOUT", "30.0"))

# Service info
service_name = "promopack-extractor"
version = "1.0"

# Database settings (for future use)
database_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# Redis settings (for future use)
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

# Secrets management (placeholder for future implementation)
use_secrets_manager = False
secrets_manager_url = os.getenv("SECRETS_MANAGER_URL", "")