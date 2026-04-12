"""Gunicorn production server configuration."""
import multiprocessing

# Workers: 2-4 x CPU cores
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Bind
bind = "0.0.0.0:8000"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Graceful shutdown
graceful_timeout = 30
