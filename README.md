# AI Resume Analyzer & Job Matcher

An NLP-based Python application that analyzes PDF resumes and compares them
with job descriptions using skill extraction and semantic similarity. It
provides match scores, skill-gap insights, recommendations, and a professional
Streamlit dashboard, backed by a FastAPI service and SQLite storage.

## Features

- PDF resume parsing
- NLP-based skill extraction from resumes and job descriptions
- Matched and missing skill detection
- Semantic similarity and final match scoring
- Resume quality analysis
- Recommendations for improving role fit
- Resume profile extraction for roles, experience, and education
- Streamlit dashboard for analysis results
- FastAPI REST API
- SQLite persistence for resumes, jobs, and analyses
- Automated API and profile-extraction tests

## Tech Stack

- Python
- PyMuPDF
- Pandas and NumPy
- Scikit-learn
- spaCy
- Sentence Transformers
- FastAPI and Uvicorn
- Streamlit
- SQLite
- Pytest-compatible test cases (currently run with Python `unittest`)
- Docker (planned; a Dockerfile is not included yet)

## Run locally

Run these commands from the repository directory. Python 3.12 is recommended.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Start the API in one terminal:

```powershell
python -m uvicorn backend.main:app --reload
```

Start the Streamlit dashboard in another terminal:

```powershell
python -m streamlit run frontend/app.py
```

Open the dashboard at `http://localhost:8501`. The API documentation is
available at `http://127.0.0.1:8000/docs`. Set `RESUME_API_URL` if the API runs
at a different address. The root launcher is also supported:

```powershell
python -m streamlit run app.py
```

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## REST API

- `POST /upload-resume` — upload a PDF resume; accepts `file`, `name`, and
  `email`, and returns a resume ID.
- `POST /analyze` — analyze a resume against a job title and description.
- `GET /analysis/{id}` — retrieve a saved analysis.
- `GET /history?email={email}` — retrieve analyses associated with an email.
- `GET /skills` — list searchable skills and categories.

## Project structure

```text
AI-Resume-Analyzer/
├── analyzer/       # PDF, NLP, matching, and scoring modules
├── backend/        # FastAPI application and API routes
├── database/       # SQLite database implementation
├── data/           # Skill catalogue
├── frontend/       # Streamlit application
├── tests/          # Automated tests
├── uploads/        # Local resume uploads (not for source control)
├── app.py          # Streamlit launcher
└── requirements.txt
```

## Privacy and deployment

Resume files and analysis records may contain personal information. Local
uploads, SQLite databases, virtual environments, and environment files are
excluded from source control by `.gitignore`. Do not commit real resumes,
database files, credentials, or secrets.

This prototype looks up history by email and does not authenticate users.
Publicly sharing the source repository is separate from exposing a running
instance: do not deploy the application to untrusted users without adding
authentication and authorization.
