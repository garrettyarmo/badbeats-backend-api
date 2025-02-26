"""
@file: worker.py
@description:
This module provides the entry point for starting Celery workers.
It imports the Celery application instance and makes it available
for the Celery worker command to use.

This file is the official entry point for running Celery workers
and consolidates the previous multiple entry points into a single,
clean implementation.

@usage:
To start a worker:
    $ celery -A app.workers.worker worker --loglevel=info

To start the beat scheduler:
    $ celery -A app.workers.worker beat --loglevel=info

To start both worker and beat scheduler:
    $ celery -A app.workers.worker worker --beat --loglevel=info

@dependencies:
- app.workers.celery_app: For Celery application instance

@notes:
- This file should not be modified as it is just an entry point
- Configuration is handled in the celery_app module
"""

from app.workers.celery_app import celery_app

# This makes the 'celery_app' importable for the Celery CLI
# No additional code needed as this serves as an entry point