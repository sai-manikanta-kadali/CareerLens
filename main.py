from pathlib import Path

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from auth_routes import get_current_user
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from database import create_mongo_client
from research_agent import InternshipResearchAgent


# Manage MongoDB connection lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):

    client = create_mongo_client()

    try:
        # Verify MongoDB connection
        client.admin.command("ping")

        app.state.mongo_client = client
        app.state.db = client["internship_research"]

        # Create unique candidate index
        app.state.db.candidates.create_index(
            "candidate_id",
            unique=True
        )

        print("MongoDB connected!")

        yield

    finally:
        client.close()
        print("MongoDB connection closed!")


# Create application
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="AI Internship Research Agent",
    version="1.0.0",
    lifespan=lifespan
)


# Request schema
class CandidateAnalysisRequest(BaseModel):

    candidate_skills: list[str] = Field(
        min_length=1,
        max_length=100
    )


# Health endpoint
@app.get("/health")
def health_check(request: Request):

    request.app.state.mongo_client.admin.command("ping")

    return {
        "status": "healthy",
        "database": "connected"
    }


# Retrieve internship records
@app.get("/jobs")
def get_jobs(request: Request):

    db = request.app.state.db

    jobs = list(
        db.jobs.find(
            {"extraction_status": "success"},
            {"_id": 0}
        )
    )

    return {
        "total_jobs": len(jobs),
        "jobs": jobs
    }




# Generate a learning roadmap from missing skills


def build_learning_roadmap(missing_skills):

    learning_plan = {

        "exploratory data analysis": {
            "objective": "Understand datasets using statistics and visualization.",
            "practice": "Analyze a real dataset using Pandas and Matplotlib."
        },

        "data preprocessing": {
            "objective": "Learn missing value handling, encoding and scaling.",
            "practice": "Clean and prepare an unprocessed dataset."
        },

        "scikit-learn": {
            "objective": "Learn model training, prediction and pipelines.",
            "practice": "Build a complete ML model using Scikit-learn."
        },

        "regression": {
            "objective": "Understand Linear Regression and prediction errors.",
            "practice": "Build a house price prediction model."
        },

        "classification": {
            "objective": "Learn classification algorithms and metrics.",
            "practice": "Build a spam email classification model."
        },

        "clustering": {
            "objective": "Understand K-Means and unsupervised learning.",
            "practice": "Create a customer segmentation project."
        },

        "model evaluation": {
            "objective": "Understand cross-validation and evaluation metrics.",
            "practice": "Evaluate an ML model using appropriate metrics."
        }
    }

    order = {
        "exploratory data analysis": 1,
        "data preprocessing": 2,
        "scikit-learn": 3,
        "regression": 4,
        "classification": 5,
        "clustering": 6,
        "model evaluation": 7
    }

    def normalize(skill):

        value = str(skill).strip().lower()
        value = " ".join(value.split())

        aliases = {
            "sklearn": "scikit-learn",
            "scikit learn": "scikit-learn"
        }

        return aliases.get(value, value)

    # Remove duplicate and non-learning requirements
    unique_skills = []
    seen = set()

    for skill in missing_skills or []:

        skill = str(skill).strip()
        key = normalize(skill)

        if not skill:
            continue

        if (
            "laptop" in key
            or "personal computer" in key
            or "own computer" in key
        ):
            continue

        if key not in seen:
            unique_skills.append(skill)
            seen.add(key)

    # Remove broad requirements when their individual topics
    # are already represented as separate missing skills
    filtered_skills = []

    for skill in unique_skills:

        key = normalize(skill)

        if "(" in key and ")" in key:

            content = key.split("(", 1)[1].rsplit(")", 1)[0]

            topics = [
                normalize(topic.strip())
                for topic in content.split(",")
                if topic.strip()
            ]

            if (
                len(topics) >= 2
                and all(topic in seen for topic in topics)
            ):
                continue

        filtered_skills.append(skill)

    ordered_skills = sorted(
        filtered_skills,
        key=lambda skill: order.get(normalize(skill), 99)
    )

    roadmap = []

    for index, skill in enumerate(ordered_skills, start=1):

        details = learning_plan.get(
            normalize(skill),
            {
                "objective": f"Understand the fundamentals of {skill}.",
                "practice": f"Complete a practical project involving {skill}."
            }
        )

        roadmap.append({
            "step": index,
            "skill": skill,
            "learning_objective": details["objective"],
            "practice_task": details["practice"]
        })

    return roadmap



@app.post("/analyze")
def analyze_candidate(
    request: Request,
    payload: CandidateAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):

    db = request.app.state.db

    # Use authenticated user ID, never trust client candidate ID
    candidate_id = current_user["user_id"]

    skills = [
        skill.strip()
        for skill in payload.candidate_skills
        if skill.strip()
    ]

    if not skills:
        raise HTTPException(
            status_code=400,
            detail="Valid candidate skills are required"
        )

    now = datetime.now(timezone.utc)

    # Save authenticated candidate profile
    db.candidates.update_one(
        {"candidate_id": candidate_id},
        {
            "$set": {
                "username": current_user["username"],
                "skills": skills,
                "updated_at": now
            },
            "$setOnInsert": {
                "created_at": now
            }
        },
        upsert=True
    )

    # Retrieve internships
    jobs = list(
        db.jobs.find(
            {"extraction_status": "success"},
            {"_id": 0}
        )
    )

    if not jobs:
        raise HTTPException(
            status_code=503,
            detail="No internship records available"
        )

    # Run ResearchAgent
    research_engine = InternshipResearchAgent(jobs)

    report = research_engine.analyze(skills)

    # Generate learning roadmap
    best_job = (
        report["ranked_jobs"][0]
        if report.get("ranked_jobs")
        else None
    )

    report["learning_roadmap"] = (
        build_learning_roadmap(
            best_job.get("missing_skills", [])
        )
        if best_job else []
    )

    # Save analysis history
    result = db.analysis_results.insert_one({
        "candidate_id": candidate_id,
        "created_at": now,
        "analysis": report
    })

    return {
        "message": "Analysis completed successfully",
        "analysis_id": str(result.inserted_id),
        "report": report
    }


# Helper to retrieve a user's own history
def load_user_history(db, candidate_id):

    records = db.analysis_results.find(
        {"candidate_id": candidate_id},
        {"_id": 1, "created_at": 1, "analysis": 1}
    ).sort("created_at", -1).limit(10)

    history = []

    for record in records:

        history.append({
            "analysis_id": str(record["_id"]),
            "created_at": record["created_at"].isoformat(),
            "analysis": record["analysis"]
        })

    return history


# Authenticated user's history
@app.get("/me/analyses")
def get_my_analysis_history(
    request: Request,
    current_user: dict = Depends(get_current_user)
):

    history = load_user_history(
        request.app.state.db,
        current_user["user_id"]
    )

    return {
        "total_records": len(history),
        "history": history
    }


# Legacy history route: verify ownership
@app.get("/candidates/{candidate_id}/analyses")
def get_analysis_history(
    candidate_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):

    if candidate_id != current_user["user_id"]:

        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's history"
        )

    history = load_user_history(
        request.app.state.db,
        current_user["user_id"]
    )

    return {
        "total_records": len(history),
        "history": history
    }



from auth_routes import router as auth_router

app.include_router(auth_router)



# Serve frontend dashboard
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

if not FRONTEND_DIR.is_dir():
    raise RuntimeError(f"Frontend folder not found: {FRONTEND_DIR}")

app.mount(
    "/dashboard",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="dashboard"
)
