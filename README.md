# AI Internship Research Agent

A full-stack internship research and skill-gap analysis application.

## Features
- JWT authentication
- FastAPI backend
- MongoDB integration
- Internship skill matching and ranking
- Missing skill analysis
- Personalized learning roadmap
- User-specific analysis history

## Tech Stack
Python, FastAPI, MongoDB, JavaScript, HTML, CSS

## Architecture
Browser Dashboard -> FastAPI -> Research Agent -> MongoDB

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Configure `.env` using `.env.example`.
3. Start: `uvicorn main:app --reload`
4. Open: `http://127.0.0.1:8000/dashboard/`

## Security
Never commit `.env`, database credentials or JWT secrets.

## Matching methodology
Match percentage represents extracted technical-skill overlap,
not the probability of being selected for an internship.
