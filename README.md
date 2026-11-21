# CareerLens — AI Internship Research Agent

**🚀 Live Demo:** [Open CareerLens](https://careerlens-z9ty.onrender.com)

A full-stack internship research and skill-gap analysis application. CareerLens compares a candidate's declared skills with structured internship requirements, ranks opportunities by technical-skill overlap, and creates a focused learning roadmap.

> Match percentages are rule-based skill-overlap indicators. They are not hiring probabilities, eligibility decisions, or guarantees of selection.

## Product capabilities

- Account registration and login with Argon2 password hashing and JWT bearer authentication.
- MongoDB-backed candidate profiles and user-specific analysis history.
- Internship listings loaded from the database.
- Normalized, deduplicated technical-skill comparison and ranked results.
- Equipment requirements and education eligibility shown separately from the technical score.
- Learning roadmap generated from missing technical skills.
- Responsive dashboard with opportunity cards, match visualizations, roadmap steps, and readable analysis history.

## Architecture

    Browser dashboard
          |
          v
    FastAPI application ---- JWT authentication
          |
          +---- InternshipResearchAgent
          |       +---- Requirement normalization
          |       +---- Skill overlap and ranking
          |       +---- Missing-skill roadmap
          |
          v
    MongoDB Atlas
       +-- users
       +-- candidates
       +-- jobs
       +-- analysis_results

## Technology

- Python 3.11+, FastAPI, Pydantic
- MongoDB Atlas / PyMongo
- JWT and Argon2 password hashing
- HTML, CSS and vanilla JavaScript
- Pytest, GitHub Actions and Docker

## Local setup

1. Create and activate a virtual environment.
2. Install application dependencies.
3. Copy .env.example to .env.
4. Set MONGODB_URI and a strong, random JWT_SECRET_KEY.
5. Seed the internship collection from the included structured sample data.
6. Start the API and open the dashboard.

    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    python scripts/seed_jobs.py
    uvicorn main:app --reload

Open http://127.0.0.1:8000/ or http://127.0.0.1:8000/dashboard/. The root URL redirects to the dashboard.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| MONGODB_URI | Yes | MongoDB connection string |
| JWT_SECRET_KEY | Yes | Random secret used to sign access tokens |

Generate a strong JWT key locally with:

    python -c "import secrets; print(secrets.token_urlsafe(48))"

Never commit .env, tokens, database credentials, or production secrets. Configure them through the hosting provider's secret/environment settings.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Database-backed health check |
| GET | /jobs | List available internship records |
| POST | /auth/register | Register a user |
| POST | /auth/login | Issue a bearer token |
| GET | /auth/me | Read the current account |
| POST | /analyze | Analyze candidate skills (authenticated) |
| GET | /me/analyses | Read the current user's history (authenticated) |
| GET | /docs | Interactive OpenAPI documentation |

Pass the login token as Authorization: Bearer token for protected endpoints.

## Data and matching methodology

The sample internship records are stored in data/jobs.json. Run python scripts/seed_jobs.py to upsert them into the internship_research.jobs collection.

The current matching baseline normalizes casing, whitespace, and a small set of common aliases. It deduplicates repeated requirements and excludes equipment such as a personal laptop from the technical-skill denominator. Education eligibility and optional skills are reported separately. The matching engine does not yet use embeddings or an LLM for semantic equivalence; exact normalized matching can miss related skills expressed with different wording.

Job details and deadlines can change. Always review the original employer listing before applying.

## Tests

Run pytest -q. GitHub Actions runs the tests and compiles the application modules on pushes and pull requests to main.

## Docker

    docker build -t careerlens .
    docker run --env-file .env -p 8000:8000 careerlens

The MongoDB database must be reachable from the container. The container listens on the PORT environment variable, defaulting to 8000.

## Project structure

    .
    ├── auth.py
    ├── auth_routes.py
    ├── database.py
    ├── main.py
    ├── research_agent.py
    ├── frontend/index.html
    ├── data/jobs.json
    ├── scripts/seed_jobs.py
    ├── tests/test_research_agent.py
    ├── Dockerfile
    ├── requirements.txt
    └── README.md

## Current limitations and production checklist

This is a portfolio project and a functional MVP, not a hiring decision system. Before production use, configure HTTPS and secure hosting, rotate secrets if they were ever exposed, add login rate limiting and account recovery, review privacy/retention requirements, monitor service health, and expand automated API/security tests. The current browser token is held in memory and is cleared when the page is refreshed.
