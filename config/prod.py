"""Production configuration."""

import os

# Environment
ENV = "prod"

# API settings
api_key_secret = os.getenv("API_KEY_SECRET", "")
langextract_api_key = os.getenv("LANGEXTRACT_API_KEY", "")

# Logging settings
log_to_file = os.getenv("LOG_TO_FILE", "true").lower() == "true"
log_level = os.getenv("LOG_LEVEL", "INFO")

# Rate limiting (stricter for prod)
rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "10"))
rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# File processing limits
max_file_size = int(os.getenv("MAX_FILE_SIZE", str(20 * 1024 * 1024)))  # 20MB
max_pages = int(os.getenv("MAX_PAGES", "1000"))

# HTTP client settings
request_timeout = float(os.getenv("REQUEST_TIMEOUT", "30.0"))

# Service info
service_name = "promopack-extractor"
version = "1.0"

# Database settings
database_url = os.getenv("DATABASE_URL", "")

# Redis settings
redis_url = os.getenv("REDIS_URL", "")

# Secrets management
use_secrets_manager = os.getenv("USE_SECRETS_MANAGER", "false").lower() == "true"
secrets_manager_url = os.getenv("SECRETS_MANAGER_URL", "")