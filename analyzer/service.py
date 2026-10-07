from pathlib import Path

from analyzer.matcher import compare_skills
from analyzer.scorer import (
    calculate_final_score,
    calculate_resume_quality,
    calculate_skill_score,
)
from analyzer.semantic_matcher import (
    calculate_semantic_similarities,
    calculate_semantic_similarity,
)
from analyzer.skill_extractor import extract_skills, load_skills
from analyzer.profile_extractor import extract_resume_profile
from analyzer.text_cleaner import clean_text


BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_PATH = BASE_DIR / "data" / "skills.csv"


def analyze_resume(resume_text: str, job_description: str) -> dict:
    cleaned_resume = clean_text(resume_text)
    cleaned_job = clean_text(job_description)
    skills = load_skills(SKILLS_PATH)
    profile = extract_resume_profile(resume_text, skills)
    resume_skills = profile["skills"]
    job_skills = extract_skills(cleaned_job, skills)
    matched_skills, missing_skills = compare_skills(
        resume_skills,
        job_skills,
    )
    skill_score = float(calculate_skill_score(matched_skills, job_skills))
    semantic_score = float(
        calculate_semantic_similarity(cleaned_resume, cleaned_job)
    )
    final_score = float(calculate_final_score(skill_score, semantic_score))

    return {
        "final_score": final_score,
        "skill_score": skill_score,
        "semantic_score": semantic_score,
        "resume_quality": calculate_resume_quality(cleaned_resume, resume_skills),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "role": profile["role"],
        "experience": profile["experience"],
        "education": profile["education"],
        "entities": profile["entities"],
    }


def recommend_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    if not jobs:
        return []

    cleaned_resume = clean_text(resume_text)
    skills = load_skills(SKILLS_PATH)
    resume_skills = extract_resume_profile(resume_text, skills)["skills"]
    cleaned_descriptions = [
        clean_text(job["description"])
        for job in jobs
    ]
    semantic_scores = calculate_semantic_similarities(
        cleaned_resume,
        cleaned_descriptions,
    )

    recommendations = []
    for job, cleaned_job, semantic_score in zip(
        jobs,
        cleaned_descriptions,
        semantic_scores,
        strict=True,
    ):
        job_skills = extract_skills(cleaned_job, skills)
        matched_skills, missing_skills = compare_skills(
            resume_skills,
            job_skills,
        )
        skill_score = calculate_skill_score(matched_skills, job_skills)
        recommendations.append(
            {
                "job_id": job["id"],
                "job_title": job["title"],
                "final_score": calculate_final_score(skill_score, semantic_score),
                "skill_score": skill_score,
                "semantic_score": semantic_score,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
            }
        )

    return sorted(
        recommendations,
        key=lambda item: (-item["final_score"], item["job_title"].casefold()),
    )