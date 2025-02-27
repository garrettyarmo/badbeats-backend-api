# BadBeats Backend API - Setup & Run Plan

This guide walks you through setting up and running the BadBeats Backend API, including database initialization, environment configuration, local testing, and deployment on Render.

## 1. Prerequisites

- **Python 3.8+**  
  Make sure Python is installed. You can check with:
  ```bash
  python --version
  ```
  or
  ```bash
  python3 --version
  ```

- **PostgreSQL**  
  We use Supabase-managed PostgreSQL by default, but you can also run Postgres locally. Ensure you have a connection string (`DATABASE_URL`) ready.

- **Redis (Optional)**  
  If you plan to run Celery workers and scheduled tasks, you need Redis. You can skip Redis if you do not need background tasks.

- **Git**  
  You need Git to clone the repository and manage code changes.

- **(Optional) Docker**  
  We provide a Dockerfile for containerization if you prefer that approach.

## 2. Environment Variables

All secrets and configuration values are stored in environment variables. An example file `.env.example` is provided at the project root. Copy or rename it to `.env` (or create a `.env.local`) and provide actual values:

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

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

LOG_LEVEL=INFO
```

**Important**: Never commit secrets to version control. Keep the `.env` file local.

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

or on Windows:

```cmd
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

This installs packages like fastapi, celery, supabase, etc.

### Configure Environment Variables

Copy `.env.example` to `.env` and fill in the details. For local Postgres, your `DATABASE_URL` might be:

```bash
DATABASE_URL=postgresql://postgres:postgrespassword@127.0.0.1:5432/badbeats_db
```

### Database Initialization & Migrations

We currently rely on Supabase or a direct table setup. For local usage, you can create a database manually:

```bash
createdb badbeats_db
```

Then set `DATABASE_URL` to point to `badbeats_db`.

**Migrations**:

- This project references Supabase, but if you need local migrations using Alembic, you can adapt that approach.
- If you have a Supabase project, run `supabase db push` or manage via the Supabase dashboard.
- Ensure the `predictions` table is created with the columns matching `app/services/prediction_service.py` references (`id`, `agent_id`, `game_id`, `pick`, `logic`, `confidence`, `result`, `created_at`, `updated_at`).

### Run the FastAPI Application Locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

By default, it listens at http://localhost:8000.

- Visit http://localhost:8000 to see the root endpoint.
- Go to http://localhost:8000/docs for the interactive API docs.

### (Optional) Running Celery (for scheduled predictions)

```bash
# In a new terminal
celery -A celery_worker worker --loglevel=info
```

If you also want to run beat (the scheduler):

```bash
celery -A celery_worker beat --loglevel=info
```

Ensure `REDIS_URL` is set in your `.env`.  
Example: `REDIS_URL=redis://127.0.0.1:6379/0`

## 4. Verifying Installation

### Health Check

Visit http://localhost:8000/api/v1/health and confirm you see:

```json
{
  "status": "OK",
  "message": "Health check successful"
}
```

### Predictions Endpoint

You can test the endpoint requiring JWT auth:

```bash
curl -X GET "http://localhost:8000/api/v1/predictions" \
  -H "Authorization: Bearer <your_token>"
```

You should see a JSON response with `"picks": [...]`.

### Authentication

Try the login flow:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -d "username=user&password=userpassword"
```

If you get a 200 with `access_token`, your server is working.

### Logging

Check your terminal logs or your designated logging solution to confirm the app logs requests.

## 5. Testing & QA

The project includes both unit tests and end-to-end tests.

### Unit Tests

```bash
pytest -xvs app/tests
```

This runs all unit and integration tests.

### End-to-End Tests

The end-to-end tests in `app/tests/e2e/test_api_flows.py` require the server running locally. You may also need playwright installed:

```bash
pip install pytest-playwright
playwright install
```

Then run:

```bash
pytest -xvs app/tests/e2e
```

Make sure `BASE_URL` in the test matches your local server (http://localhost:8000).

### Coverage

You can add coverage with:

```bash
coverage run -m pytest && coverage report -m
```

## 6. Deploying on Render

Below is a high-level approach for deploying to Render. You can adapt this to other cloud platforms.

### 6.1. Create a New Render Web Service

1. Link your GitHub repository to Render or use manual deployment.

2. Set up the environment: Provide environment variables in Render's dashboard to match your `.env`. This includes:
   - `DATABASE_URL`
   - `JWT_SECRET`
   - `REDIS_URL` (optionally, if you're using Celery)
   - `BALL_DONT_LIE_API_KEY`
   - `OPENAI_API_KEY` or `GROQ_API_KEY`
   - And so on.

3. **Specify Start Command**  
   For the main web service:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 10000
   ```
   (Render expects your app to listen on port 10000 by default; confirm in the Render docs.)

4. **Install Dependencies**
   - Render can automatically install from `requirements.txt`.

5. **Build & Deploy**
   - Render will pull your code, build it, install the dependencies, then run uvicorn.

6. **Celery Workers on Render**
   - If you want background tasks, create another Background Worker in Render with a start command:
     ```bash
     celery -A celery_worker worker --loglevel=info
     ```
   - Optionally, create a separate worker for Celery Beat if you want scheduling:
     ```bash
     celery -A celery_worker beat --loglevel=info
     ```
   - Make sure you set the same environment variables in the worker environment.

### 6.2. Database Migrations on Render

Because we rely on Supabase or direct Postgres, you can do one of the following:

- **Use Supabase**: Let Supabase handle migrations. In your `.env` on Render, just ensure your `DATABASE_URL` points to your Supabase instance.
- **Manual DB Setup**: If you have Alembic or a custom migration approach, create a script or Docker command that runs your migrations on startup. Alternatively, run migrations via a separate process before starting the web app.

### 6.3. Post-Deployment Checks

- Check logs in Render to confirm the server started successfully.
- Visit your service URL (https://yourappname.onrender.com/api/v1/health) to confirm the health check.
- Test predictions with a real request to confirm JWT and DB connectivity.

## 7. Further Notes & Best Practices

### Security

- Always run behind HTTPS in production.
- Configure the `CORS_ALLOW_ORIGINS` in production for only your domain.
- Use strong secrets and rotate them regularly.

### Performance

- Use gunicorn or uvicorn workers for concurrency.
- Use a separate process for Celery tasks to avoid blocking main requests.

### Scaling

- If your usage grows, move the Celery worker and Redis onto dedicated instances.
- Add logging and monitoring (ELK, Prometheus, or Render's logs) for real-time tracking.

### Troubleshooting

- Check environment variables on Render for typos.
- Check logs for DB connection failures.
- Validate your `.env` matches production secrets.

## 8. Summary

You now have a complete overview of how to set up and run the BadBeats Backend API:

1. Set environment variables
2. Install Python dependencies and create the database
3. Run the FastAPI app locally or on Render
4. Enable Celery + Redis for background tasks if needed
5. Test endpoints using unit or e2e tests
6. Deploy with environment variables on Render or another platform

Once deployed, your new AI-driven sports betting picks service should be accessible via the specified domain or IP.
