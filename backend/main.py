from contextlib import asynccontextmanager
from pathlib import Path
import re
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from analyzer.pdf_reader import extract_text_from_pdf
from analyzer.service import analyze_resume, recommend_jobs
from database.db import (
    add_analysis,
    add_resume,
    get_analysis,
    get_or_create_job,
    get_or_create_user,
    get_resume,
    init_db,
    list_jobs,
    list_user_analyses,
)


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
SKILLS_PATH = BASE_DIR / "data" / "skills.csv"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="AI Resume Analyzer API", version="4.0.0", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    resume_id: str
    job_title: str = Field(default="Untitled job", min_length=1, max_length=200)
    job_description: str = Field(min_length=1, max_length=50000)


@app.post("/upload-resume", status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    name: str = Form(default="Guest", max_length=120),
    email: str = Form(default="guest@local.invalid", max_length=254),
):
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Only PDF resumes are supported.")

    name = name.strip()
    email = email.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF must be 10 MB or smaller.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    resume_id = str(uuid4())
    file_path = UPLOADS_DIR / f"{resume_id}.pdf"
    file_path.write_bytes(content)
    try:
        user_id = get_or_create_user(name, email)
        add_resume(resume_id, user_id, Path(file.filename).name, str(file_path))
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    return {
        "resume_id": resume_id,
        "file_name": Path(file.filename).name,
        "name": name,
        "email": email,
    }


@app.post("/analyze", status_code=201)
def analyze(request: AnalyzeRequest):
    resume = get_resume(request.resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume upload was not found.")

    resume_text = extract_text_from_pdf(resume["file_path"])
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the PDF.")

    result = analyze_resume(resume_text, request.job_description)
    job_id = get_or_create_job(request.job_title.strip(), request.job_description.strip())
    recommendations = recommend_jobs(resume_text, list_jobs())
    analysis_id = str(uuid4())
    add_analysis(analysis_id, request.resume_id, job_id, result)
    return {
        "id": analysis_id,
        "resume_id": request.resume_id,
        "result": result,
        "recommendations": recommendations,
    }


@app.get("/recommendations/{resume_id}")
def read_recommendations(resume_id: str):
    resume = get_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume upload was not found.")

    resume_text = extract_text_from_pdf(resume["file_path"])
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the PDF.")

    return {
        "resume_id": resume_id,
        "recommendations": recommend_jobs(resume_text, list_jobs()),
    }


@app.get("/analysis/{analysis_id}")
def read_analysis(analysis_id: str):
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis was not found.")
    return analysis


@app.get("/history")
def read_history(email: str = Query(min_length=1, max_length=254)):
    normalized_email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return {"analyses": list_user_analyses(normalized_email)}


@app.get("/skills")
def list_skills():
    skills = pd.read_csv(SKILLS_PATH).fillna("")
    return {
        "skills": [
            {"skill": str(row.skill), "category": str(row.category)}
            for row in skills.itertuples(index=False)
        ]
    }