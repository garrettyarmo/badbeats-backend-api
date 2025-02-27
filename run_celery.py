"""
@file: run_celery.py
@description:
DEPRECATED: Please use celery_worker.py instead.

This file is kept for backward compatibility but will be removed in a future update.
All functionality has been moved to celery_worker.py for cleaner organization.

@usage:
Instead of using this file, please use:
    $ python celery_worker.py worker --loglevel=info

@dependencies:
- celery: For task processing
"""

import os
import sys
import warnings

warnings.warn(
    "run_celery.py is deprecated. Please use celery_worker.py instead.",
    DeprecationWarning,
    stacklevel=2
)

from celery import Celery
from app.core.config import settings

# Create a minimal Celery app
app = Celery('badbeats', broker=settings.REDIS_URL)

# Configure the Celery app
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True
)

# Load tasks later - this is just to get the worker running
app.conf.task_routes = {
    "app.workers.tasks.*": {"queue": "default"},
}

if __name__ == '__main__':
    # Print deprecation message
    print("WARNING: run_celery.py is deprecated. Please use celery_worker.py instead.")
    
    # Launch the worker directly with proper arguments
    worker_args = ['worker', '--loglevel=info']
    sys.argv = [sys.argv[0]] + worker_args
    app.worker_main(argv=sys.argv)