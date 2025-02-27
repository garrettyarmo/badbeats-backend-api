"""
@file: celery_worker.py
@description:
This is a simplified entry point for starting Celery workers that avoids complex
import paths. It's placed at the project root to minimize import errors.

This script consolidates the previous multiple entry points into a single,
clean implementation that redirects to the main worker module.

@usage:
To start a worker:
    $ celery -A celery_worker worker --loglevel=info

To start the beat scheduler:
    $ celery -A celery_worker beat --loglevel=info

To start both worker and beat scheduler:
    $ celery -A celery_worker worker --beat --loglevel=info

@dependencies:
- app.workers.celery_app: For Celery configuration

@notes:
- This file is meant to be run from the project root directory
- The actual Celery configuration is in app.workers.celery_app
"""

from app.workers.celery_app import celery_app

# This makes the Celery app importable by the Celery command-line interface
app = celery_app

if __name__ == '__main__':
    print("ERROR: This file should not be executed directly.")
    print("Please use the celery command instead:")
    print("  $ celery -A celery_worker worker --loglevel=info")
    print("  $ celery -A celery_worker beat --loglevel=info")
    print("  $ celery -A celery_worker worker --beat --loglevel=info")