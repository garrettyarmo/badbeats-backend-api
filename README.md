# BadBeats Backend API

**Version:** 0.1.0  
**Status:** Development

## Overview

BadBeats is an AI-driven sports betting backend API that generates Against The Spread (ATS) predictions for NBA games. The system ingests structured data (NBA stats, odds) from the Ball Don't Lie API and unstructured data (news, injury reports) from sources like ESPN, NBA.com, and Bleacher Report. Predictions are generated using direct OpenAI API calls, processed synchronously, and exposed via secure RESTful endpoints. The architecture is modular, supporting future expansions such as additional prediction models or sports.

## Key Features

- **Data Ingestion**: Fetches NBA game schedules, team/player stats, odds, and news data daily.
- **Prediction Generation**: Uses OpenAI's LLM to produce ATS predictions with confidence scores and reasoning.
- **API Endpoints**: Offers secure, versioned RESTful endpoints for accessing predictions.
- **Authentication & Security**: Implements OAuth2 with JWT for API access control.
- **Storage & Retrieval**: Stores predictions and historical game data in a PostgreSQL (Supabase) database.
- **Logging & Monitoring**: Provides centralized logging for debugging and monitoring.

## Repository Structure

The repository is organized as follows:

    /backend
    ├── app/
    │   ├── api/        # API endpoints and routes (health, predictions, auth)
    │   ├── core/       # Core configurations, authentication, logging, middleware
    │   ├── db/         # Database client and utilities (Supabase integration)
    │   ├── llm/        # Prediction model implementations (OpenAI-based)
    │   ├── schemas/    # Pydantic models for request/response validation
    │   ├── services/   # Business logic and external API integrations
    │   ├── storage/    # File storage utilities (currently minimal)
    │   ├── tests/      # Unit, integration, and end-to-end tests
    │   ├── workers/    # Workflow utilities for data ingestion and predictions
    ├── .env            # Environment variables (not tracked)
    ├── requirements.txt # Python dependencies
    ├── Dockerfile      # Containerization configuration
    └── main.py         # Application entry point

For a detailed architecture overview and data flow diagram, refer to [ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Getting Started

1. **Environment Setup**:  
   - Ensure Python 3.8+ is installed.  
   - Set up a PostgreSQL database via Supabase and update `DATABASE_URL` in `.env`.  
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```

2. **Running the Application**:  
   - Start the FastAPI server:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
     ```
   - Access endpoints at `http://localhost:8000` (e.g., `/docs` for API docs).

3. **Running the Prediction Workflow**:  
   - Execute the workflow manually or schedule it (e.g., via cron):
     ```bash
     python -m app.services.prediction_workflow
     ```
   - Example cron job (daily at 2 AM):
     ```bash
     0 2 * * * /path/to/python /path/to/app/services/prediction_workflow.py >> /path/to/logfile.log 2>&1
     ```

4. **Testing**:  
   - Run unit and integration tests:
     ```bash
     pytest app/tests
     ```
   - For end-to-end tests with Playwright:
     ```bash
     pip install pytest-playwright
     playwright install
     pytest app/tests/e2e
     ```

## Architecture and Code Flow

The architecture follows a Directed Acyclic Graph (DAG) pattern where data flows from external sources through ingestion services to storage, then to the prediction engine, and finally to API endpoints. Key modules have distinct responsibilities with well-defined interfaces. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Contributing

- Adhere to coding standards in the project documentation.
- Accompany new code with tests in `app/tests`.
- Update documentation for significant changes.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.