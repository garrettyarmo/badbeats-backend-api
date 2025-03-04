# BadBeats Backend API - Setup & Run Plan

This guide walks you through setting up and running the BadBeats Backend API, including database initialization, environment configuration, local testing, and deployment on Render.

## 1. Prerequisites

- **Python 3.8+**  
  Verify with:
  ```bash
  python --version
  ```
  or
  ```bash
  python3 --version
  ```

- **PostgreSQL**  
  Uses Supabase-managed PostgreSQL by default. For local use, ensure a connection string (DATABASE_URL) is available.

- **Git**  
  Required to clone the repository and manage code changes.

- **(Optional) Docker**  
  A Dockerfile is provided for containerized deployment.

## 2. Environment Variables

Configuration is managed via environment variables. Copy `.env.example` to `.env` and populate it:

```ini
APP_ENV=development
DEBUG=True
SECRET_KEY=your_secret_key_here

DATABASE_URL=postgresql://postgres:[password]@db.[instance].supabase.co:5432/postgres

JWT_SECRET=your_jwt_secret_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

BALL_DONT_LIE_API_KEY=your_nba_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here

LOG_LEVEL=INFO
```

**Important**: Do not commit `.env` to version control. Store secrets securely.

## 3. Local Setup

### Clone the Repository

```bash
git clone https://github.com/your-org/garrettyarmo-badbeats-backend-api.git
cd garrettyarmo-badbeats-backend-api
```

### Create and Activate a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```cmd
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

Installs FastAPI, Supabase, OpenAI, and other required packages.

### Configure Environment Variables

Copy `.env.example` to `.env` and fill in values. For local Postgres:

```bash
DATABASE_URL=postgresql://postgres:postgrespassword@127.0.0.1:5432/badbeats_db
```

### Database Initialization

For local Postgres:

```bash
createdb badbeats_db
```

For Supabase, use the dashboard or CLI (`supabase db push`) to create tables:

- **predictions**: id (uuid), agent_id, game_id, pick, logic, confidence, result, created_at, updated_at
- **games**: id, game_data (jsonb), created_at, updated_at

Set `DATABASE_URL` to point to your database.

### Run the FastAPI Application Locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Access at http://localhost:8000:

- Root: http://localhost:8000/
- API Docs: http://localhost:8000/docs

### Running the Workflows

#### Data Ingestion: 
Run daily to update structured data:

```bash
python -m app.services.prediction_workflow run_data_ingestion
```

Schedule with cron (e.g., 2 AM daily):

```bash
crontab -e
0 2 * * * /path/to/python /path/to/app/services/prediction_workflow.py run_data_ingestion >> /path/to/logfile.log 2>&1
```

#### Prediction Generation: 
Run hourly to generate predictions for upcoming games:

```bash
python -m app.services.prediction_workflow run_prediction_generation
```

Schedule with cron (e.g., every hour):

```bash
crontab -e
0 * * * * /path/to/python /path/to/app/services/prediction_workflow.py run_prediction_generation >> /path/to/logfile.log 2>&1
```

## 4. Verifying Installation

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{"status": "OK", "message": "Health check successful"}
```

### Predictions Endpoint

Requires JWT:

```bash
curl -X GET "http://localhost:8000/api/v1/predictions" -H "Authorization: Bearer <your_token>"
```

Returns:

```json
{"picks": [...]}
```

### Authentication

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" -d "username=user&password=userpassword"
```

Returns a JWT token on success.

## 5. Testing & QA

### Unit Tests

```bash
pytest -xvs app/tests
```

### End-to-End Tests

Requires Playwright:

```bash
pip install pytest-playwright
playwright install
pytest -xvs app/tests/e2e
```

Ensure the server is running at http://localhost:8000.

### Coverage

```bash
coverage run -m pytest && coverage report -m
```

## 6. Deploying on Render

### 6.1. Create a New Render Web Service

- Link your GitHub repository to Render.
- Set environment variables in Render's dashboard matching `.env`.
- Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

Render installs dependencies from `requirements.txt` and deploys.

### 6.2. Running the Workflows on Render

- **Data Ingestion**: Use Render's cron job feature to run daily:
  - Command: `python -m app.services.prediction_workflow run_data_ingestion`
  - Schedule: `0 2 * * *` (2 AM UTC)
- **Prediction Generation**: Use Render's cron job feature to run hourly:
  - Command: `python -m app.services.prediction_workflow run_prediction_generation`
  - Schedule: `0 * * * *` (every hour)

### 6.3. Database on Render

Use Supabase with `DATABASE_URL` set in the environment. Manage tables via Supabase dashboard or CLI.

### 6.4. Post-Deployment Checks

- Verify logs in Render.
- Test: https://yourapp.onrender.com/api/v1/health
- Test predictions with a JWT-authenticated request.

## 7. Further Notes & Best Practices

### Security

- Enforce HTTPS in production.
- Restrict CORS origins to your frontend domain.
- Rotate secrets regularly.

### Performance

- Use gunicorn for concurrency: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`.

### Scaling

- Consider caching frequently accessed data.
- Monitor with tools like Render logs or ELK.

### Troubleshooting

- Check `.env` for errors.
- Review logs for DB or API issues.

## 8. Summary

- Configure environment variables.
- Install dependencies and set up the database.
- Run FastAPI locally or on Render.
- Schedule data ingestion daily and prediction generation hourly.
- Test with unit and e2e tests.
- Deploy to Render with environment setup.