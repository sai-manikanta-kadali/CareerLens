from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth_routes import get_current_user, router as auth_router
from database import create_mongo_client
from research_agent import InternshipResearchAgent


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_mongo_client()
    try:
        client.admin.command("ping")
        db = client["internship_research"]
        db.users.create_index("username", unique=True)
        db.candidates.create_index("candidate_id", unique=True)
        db.analysis_results.create_index([("candidate_id", 1), ("created_at", -1)])
        app.state.mongo_client = client
        app.state.db = db
        print("MongoDB connected!")
        yield
    finally:
        client.close()
        print("MongoDB connection closed!")


app = FastAPI(
    title="AI Internship Research Agent",
    description="Research internship requirements, compare candidate skills, and generate focused learning recommendations.",
    version="1.1.0",
    lifespan=lifespan,
)


class CandidateAnalysisRequest(BaseModel):
    candidate_skills: list[str] = Field(min_length=1, max_length=100)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/dashboard/")


@app.get("/health", tags=["System"])
def health_check(request: Request):
    request.app.state.mongo_client.admin.command("ping")
    return {"status": "healthy", "database": "connected"}


@app.get("/jobs", tags=["Internships"])
def get_jobs(request: Request):
    jobs = list(
        request.app.state.db.jobs.find(
            {"extraction_status": "success"},
            {"_id": 0},
        )
    )
    return {"total_jobs": len(jobs), "jobs": jobs}


def build_learning_roadmap(missing_skills):
    learning_plan = {
        "exploratory data analysis": {
            "objective": "Understand datasets using statistics and visualization.",
            "practice": "Analyze a real dataset using Pandas and Matplotlib.",
        },
        "data preprocessing": {
            "objective": "Learn missing-value handling, encoding and scaling.",
            "practice": "Clean and prepare an unprocessed dataset.",
        },
        "scikit-learn": {
            "objective": "Learn model training, prediction and pipelines.",
            "practice": "Build a complete ML model using Scikit-learn.",
        },
        "regression": {
            "objective": "Understand Linear Regression and prediction errors.",
            "practice": "Build a house-price prediction model.",
        },
        "classification": {
            "objective": "Learn classification algorithms and evaluation metrics.",
            "practice": "Build a spam-email classification model.",
        },
        "clustering": {
            "objective": "Understand K-Means and unsupervised learning.",
            "practice": "Create a customer-segmentation project.",
        },
        "model evaluation": {
            "objective": "Understand cross-validation and evaluation metrics.",
            "practice": "Evaluate an ML model using appropriate metrics.",
        },
    }
    order = {
        "exploratory data analysis": 1,
        "data preprocessing": 2,
        "scikit-learn": 3,
        "regression": 4,
        "classification": 5,
        "clustering": 6,
        "model evaluation": 7,
    }

    def normalize(skill):
        value = " ".join(str(skill or "").strip().lower().split())
        return {"sklearn": "scikit-learn", "scikit learn": "scikit-learn"}.get(value, value)

    unique = []
    seen = set()
    for skill in missing_skills or []:
        label = str(skill or "").strip()
        key = normalize(label)
        if not label or key in seen:
            continue
        if any(term in key for term in ("laptop", "personal computer", "own computer")):
            continue
        unique.append(label)
        seen.add(key)

    filtered = []
    for skill in unique:
        key = normalize(skill)
        if "(" in key and ")" in key:
            content = key.split("(", 1)[1].rsplit(")", 1)[0]
            topics = [normalize(part) for part in content.split(",") if part.strip()]
            if len(topics) >= 2 and all(topic in seen for topic in topics):
                continue
        filtered.append(skill)

    ordered = sorted(filtered, key=lambda item: order.get(normalize(item), 99))
    roadmap = []
    for index, skill in enumerate(ordered, start=1):
        details = learning_plan.get(
            normalize(skill),
            {
                "objective": f"Understand the fundamentals of {skill}.",
                "practice": f"Complete a practical project involving {skill}.",
            },
        )
        roadmap.append({
            "step": index,
            "skill": skill,
            "learning_objective": details["objective"],
            "practice_task": details["practice"],
        })
    return roadmap


@app.post("/analyze", tags=["Analysis"])
def analyze_candidate(
    request: Request,
    payload: CandidateAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    db = request.app.state.db
    candidate_id = current_user["user_id"]
    skills = [
        str(skill).strip()
        for skill in payload.candidate_skills
        if str(skill or "").strip()
    ]
    if not skills:
        raise HTTPException(status_code=400, detail="Valid candidate skills are required.")

    now = datetime.now(timezone.utc)
    db.candidates.update_one(
        {"candidate_id": candidate_id},
        {
            "$set": {
                "username": current_user["username"],
                "skills": skills,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    jobs = list(
        db.jobs.find({"extraction_status": "success"}, {"_id": 0})
    )
    if not jobs:
        raise HTTPException(status_code=503, detail="No internship records available.")

    report = InternshipResearchAgent(jobs).analyze(skills)
    best_job = report["ranked_jobs"][0] if report["ranked_jobs"] else None
    report["learning_roadmap"] = build_learning_roadmap(
        best_job.get("missing_skills", []) if best_job else []
    )

    result = db.analysis_results.insert_one({
        "candidate_id": candidate_id,
        "created_at": now,
        "analysis": report,
    })
    return {
        "message": "Analysis completed successfully.",
        "analysis_id": str(result.inserted_id),
        "report": report,
    }


def load_user_history(db, candidate_id):
    records = db.analysis_results.find(
        {"candidate_id": candidate_id},
        {"_id": 1, "created_at": 1, "analysis": 1},
    ).sort("created_at", -1).limit(10)
    return [
        {
            "analysis_id": str(record["_id"]),
            "created_at": record["created_at"].isoformat(),
            "analysis": record["analysis"],
        }
        for record in records
    ]


@app.get("/me/analyses", tags=["Analysis"])
def get_my_analysis_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    history = load_user_history(request.app.state.db, current_user["user_id"])
    return {"total_records": len(history), "history": history}


@app.get("/candidates/{candidate_id}/analyses", tags=["Analysis"])
def get_analysis_history(
    candidate_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    if candidate_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="You cannot access another user's history.")
    history = load_user_history(request.app.state.db, current_user["user_id"])
    return {"total_records": len(history), "history": history}


app.include_router(auth_router)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
if not FRONTEND_DIR.is_dir():
    raise RuntimeError(f"Frontend folder not found: {FRONTEND_DIR}")
app.mount("/dashboard", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="dashboard")
