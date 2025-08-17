"""
Uvicorn Configuration for Production
Windows-compatible settings for FastAPI application
"""
import os
import multiprocessing

# Server configuration
host = "0.0.0.0"
port = 8000
# Calculate workers based on CPU cores (2 * cores + 1) but limit for Windows compatibility
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Max 4 workers for Windows stability

# Logging configuration
log_level = "info"
access_log = True
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "access": {
            "format": '%(asctime)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "default",
            "class": "logging.FileHandler",
            "filename": "./logs/app.log",
            "mode": "a",
        },
        "access_file": {
            "formatter": "access",
            "class": "logging.FileHandler",
            "filename": "./logs/access.log",
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["default", "file"],
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["access", "access_file"],
            "propagate": False,
        },
    },
}

# SSL configuration (uncomment for HTTPS)
# ssl_keyfile = "/path/to/keyfile.pem"
# ssl_certfile = "/path/to/certfile.pem"

# Performance settings
reload = False  # Set to False in production
reload_dirs = None
loop = "auto"  # Use the best available loop
http = "auto"  # Use the best available HTTP implementation

# Worker timeout and limits
timeout_keep_alive = 5
timeout_graceful_shutdown = 30

# Application settings
app = "web.app:app"
factory = False

# Environment variables
env_file = ".env"

# Interface and socket settings
uds = None  # Unix domain socket (not used on Windows)
fd = None   # File descriptor (not used on Windows)

# Development settings (disabled in production)
debug = False
