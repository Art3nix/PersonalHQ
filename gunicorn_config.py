"""Gunicorn configuration for production deployment."""

import multiprocessing
import os

# Worker configuration
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Request handling
max_requests = 1000
max_requests_jitter = 100

# Server socket
bind = '0.0.0.0:8000'

# Logging
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', '-')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Process naming
proc_name = 'personalhq'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed, set via environment variables)
keyfile = os.environ.get('GUNICORN_KEYFILE', None)
certfile = os.environ.get('GUNICORN_CERTFILE', None)

# Application
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED_PROTOCOL': 'ssl',
    'X-FORWARDED_PROTO': 'https',
    'X-FORWARDED_SSL': 'on',
}
