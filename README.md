# BadBeats Backend API

A sophisticated backend API that generates AI-driven sports betting picks for the NBA. The system ingests structured data (NBA stats, odds) and unstructured data (news, injury reports) to inform a LangChain-powered LLM, which generates predictions against the spread (ATS).

## Features

### Data Ingestion
- Integration with NBA API for game schedules, team stats, and player stats
- Live odds data integration via The Odds API
- Unstructured data ingestion from news sources (ESPN, NBA.com)

### Prediction Models
- LangChain-powered LLM for ATS predictions
- Modular framework for independent models
- Confidence scoring for each prediction

### API Endpoints
- Secure, versioned API for betting picks
- Structured JSON responses with detailed prediction information
- Authentication and rate limiting

### Storage & Retrieval
- PostgreSQL database for predictions storage
- Scheduled prediction process (one hour before each game)
- Historical data analysis

## Tech Stack

- **Backend**: FastAPI, PostgreSQL, SQLAlchemy
- **Auth**: OAuth2, JWT (via FastAPI security)
- **LLM/AI**: LangChain, OpenAI/Groq API
- **Task Queues**: Celery/Redis
- **Testing**: Pytest

## Project Structure

/backend
├── app/
│   ├── api/        # API endpoints
│   ├── db/         # Database models, schemas, and queries
│   ├── services/   # Business logic and integrations
│   ├── workers/    # Background tasks and Celery workers
│   ├── core/       # Configs, authentication, utilities
│   ├── schemas/    # Pydantic schemas for validation
│   ├── llm/        # GenAI and LangChain components
│   ├── storage/    # File handling logic
│   ├── tests/      # Unit and integration tests
├── .env           # Environment variables
├── requirements.txt # Dependencies
├── Dockerfile     # Containerization config
├── README.md      # Documentation

## Setup and Installation

1. Clone the repository:

git clone https://github.com/garrettyarmo/badbeats-backend-api.git
cd badbeats-backend-api

2. Create and activate a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:

pip install -r requirements.txt

4. Set up environment variables:

cp .env.example .env
Edit .env with your configuration

5. Run the application:

python main.py

## API Documentation

Once the server is running, access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Testing

Run tests with pytest:

pytest app/tests

### Code Style

This project follows PEP 8 style guidelines. Use tools like flake8 and black for linting and formatting:

flake8 app
black app

## License

This project is licensed under the MIT License - see the LICENSE file for details.