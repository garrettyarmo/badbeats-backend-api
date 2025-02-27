# BadBeats API Test Suite

This directory contains the test suite for the BadBeats API. The tests are organized by functionality and are designed to be run with pytest.

## Test Structure

- `conftest.py`: Contains pytest fixtures and configuration
- `test_auth.py`: Tests for authentication functionality
- `test_llm.py`: Tests for LLM integration and prediction models
- `test_middleware.py`: Tests for FastAPI middleware components
- `test_predictions.py`: Tests for prediction API endpoints and services
- `test_services.py`: Tests for external API integration services
- `test_workers.py`: Tests for Celery task workers

## Running Tests

To run the tests, use the following command from the project root:

```bash
pytest -xvs app/tests