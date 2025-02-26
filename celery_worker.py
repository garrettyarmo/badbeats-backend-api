"""
@file: celery_worker.py
@description:
This is a simplified entry point for starting Celery workers that avoids complex
import paths. It's placed at the project root to minimize import errors.

This script consolidates the previous multiple entry points into a single,
clean implementation that redirects to the main worker module.

@usage:
To start a worker:
    $ python celery_worker.py worker --loglevel=info

To start the beat scheduler:
    $ python celery_worker.py beat --loglevel=info

To start both worker and beat scheduler:
    $ python celery_worker.py worker --beat --loglevel=info

@dependencies:
- app.workers.celery_app: For Celery configuration

@notes:
- This file is meant to be run from the project root directory
- The actual Celery configuration is in app.workers.celery_app
"""

from app.workers.celery_app import celery_app

if __name__ == '__main__':
    celery_app.start()