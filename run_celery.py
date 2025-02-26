"""
@file: run_celery.py
@description:
A simple entry point for starting the Celery worker. This avoids complex import
chains at startup and makes it easier to debug initialization issues.

@usage:
To start a worker:
    $ python run_celery.py

@dependencies:
- celery: For task processing
"""

import os
import sys
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
    # Launch the worker directly with proper arguments
    worker_args = ['worker', '--loglevel=info']
    sys.argv = [sys.argv[0]] + worker_args
    app.worker_main(argv=sys.argv)