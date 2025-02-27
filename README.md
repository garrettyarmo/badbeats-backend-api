# BadBeats Backend API

**Version:** 0.1.0  
**Status:** Development

## Overview

BadBeats is an AI-driven sports betting backend API that generates Against The Spread (ATS) predictions for NBA games. The system ingests structured data (NBA stats, odds) and unstructured data (news, injury reports) to inform a LangChain-powered LLM that generates predictions. The architecture is modular and designed for scalability, allowing integration of additional prediction models and data sources in the future.

## Key Features

- **Data Ingestion**: Ingests NBA game schedules, team/player stats, odds, and news data.
- **Prediction Generation**: Uses a LangChain-powered LLM to generate ATS predictions along with confidence scores and detailed logic.
- **API Endpoints**: Provides secure, versioned RESTful endpoints for predictions.
- **Authentication & Security**: Utilizes OAuth2 and JWT for securing API access.
- **Storage & Retrieval**: Stores predictions in a PostgreSQL (Supabase) database with historical analysis capabilities.
- **Task Scheduling**: Employs Celery and Redis to schedule predictions (one hour before each game) and handle background tasks.
- **Logging & Monitoring**: Centralized logging and middleware for monitoring API usage and errors.

## Repository Structure

The repository is organized as follows:

    /backend
    ├── app/
    │   ├── api/        # API endpoints and routes (health, predictions, auth)
    │   ├── core/       # Core configurations, authentication, logging, middleware
    │   ├── db/         # Database models, session management, and migrations
    │   ├── llm/        # LangChain and prediction model implementations
    │   ├── schemas/    # Pydantic models for request and response validation
    │   ├── services/   # Business logic and external API integrations
    │   ├── storage/    # File storage integration (Supabase)
    │   ├── tests/      # Unit, integration, and end-to-end tests
    │   └── workers/    # Celery tasks and worker configuration
    ├── .env            # Environment variables and secrets
    ├── requirements.txt # Python dependencies
    ├── Dockerfile      # Containerization configuration
    └── main.py         # Application entry point


For a detailed architecture overview and data flow diagram, please refer to [ARCHITECTURE.md](ARCHITECTURE.md).

## Getting Started

1. **Environment Setup**:  
   - Ensure Python (3.8+) is installed.  
   - Set up a PostgreSQL database and update the `DATABASE_URL` and other required environment variables in `.env`.  
   - Install dependencies with `pip install -r requirements.txt`.

2. **Running the Application**:  
   - Start the FastAPI application using `uvicorn main:app --reload`.
   - Use tools like Postman or your browser to access the API endpoints.

3. **Task Scheduling**:  
   - Start Celery workers using `celery -A celery_worker worker --loglevel=info`.
   - For periodic tasks, start the Celery beat scheduler as well.

4. **Testing**:  
   - Run unit and integration tests using `pytest`.
   - End-to-end tests are provided using Playwright; see `app/tests/e2e/test_api_flows.py` for details.

## Architecture and Code Flow

The project’s architecture is designed as a Directed Acyclic Graph (DAG) where data flows from external sources through ingestion services, is processed by prediction models, and then exposed via secure API endpoints. Each module has a clear responsibility and interacts through well-defined interfaces.

For a detailed breakdown, please see [ARCHITECTURE.md](ARCHITECTURE.md).

## Contributing

- Follow the project coding standards as detailed in the repository documentation.
- Ensure all new code is accompanied by relevant tests.
- Document any changes in both code and architecture diagrams.

## License

This project is licensed under the MIT License.