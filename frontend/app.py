import os
from html import escape

import requests
import streamlit as st


API_URL = os.getenv("RESUME_API_URL", "http://127.0.0.1:8000").rstrip("/")


def request_error(response: requests.Response) -> str:
    try:
        detail = response.json().get("detail", response.text)
    except ValueError:
        detail = response.text
    return str(detail)


def show_result(result: dict, resume_name: str = "Uploaded resume") -> None:
    matched_skills = result.get("matched_skills", [])
    missing_skills = result.get("missing_skills", [])

    st.header("Your Resume Match")
    st.caption(f"Resume: {resume_name}")

    with st.container(border=True):
        score_col, summary_col = st.columns([1, 3], vertical_alignment="center")
        with score_col:
            st.metric("Final Match Score", f"{float(result['final_score']):.0f}%")
        with summary_col:
            st.markdown("**Overall fit for this role**")
            st.progress(
                min(max(float(result["final_score"]) / 100, 0.0), 1.0),
                text="Resume and job description match",
            )

    skill_col, semantic_col, quality_col = st.columns(3)
    skill_col.metric("Skill Match", f"{float(result['skill_score']):.0f}%")
    semantic_col.metric(
        "Semantic Match",
        f"{float(result['semantic_score']):.0f}%",
    )
    quality_col.metric(
        "Resume Quality",
        f"{float(result['resume_quality']):.0f}%",
    )

    st.divider()
    matched_col, missing_col = st.columns(2)
    with matched_col:
        with st.container(border=True):
            st.subheader("✅ Matched Skills")
            if matched_skills:
                badges = "".join(
                    f'<span class="skill-badge matched">✓ {escape(str(skill).title())}</span>'
                    for skill in matched_skills
                )
                st.markdown(
                    f'<div class="skill-list">{badges}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("No matching skills found.")

    with missing_col:
        with st.container(border=True):
            st.subheader("⚠️ Missing Skills")
            if missing_skills:
                badges = "".join(
                    f'<span class="skill-badge missing">✗ {escape(str(skill).title())}</span>'
                    for skill in missing_skills
                )
                st.markdown(
                    f'<div class="skill-list">{badges}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.success("No major missing skills detected.")

    with st.container(border=True):
        st.subheader("💡 Recommendations")
        if missing_skills:
            for skill in missing_skills:
                st.markdown(
                    f"→ Build a project or practice using **{escape(str(skill).title())}**"
                )
        else:
            st.markdown("→ Keep your resume aligned with the role requirements.")
        st.markdown("→ Add relevant project or work experience with measurable results.")

    with st.expander("Resume profile and additional analysis"):
        st.markdown("**Skills found in resume**")
        st.write(", ".join(result.get("resume_skills", [])) or "No listed skills found.")
        st.markdown("**Skills required by job**")
        st.write(", ".join(result.get("job_skills", [])) or "No listed skills found.")

        roles = result.get("role", [])
        st.write(f"Role: {', '.join(roles) or 'Not detected'}")

        experiences = result.get("experience", [])
        durations = [item["duration"] for item in experiences]
        st.write(f"Experience: {', '.join(durations) or 'Not detected'}")

        education = result.get("education", {})
        degrees = education.get("degrees", [])
        institutions = education.get("institutions", [])
        st.write(f"Education: {', '.join(degrees) or 'Not detected'}")
        st.write(f"Institutions: {', '.join(institutions) or 'Not detected'}")

        entities = result.get("entities", [])
        if entities:
            st.markdown("**Named entities detected by spaCy**")
            st.write(
                ", ".join(
                    f"{entity['text']} ({entity['label']})"
                    for entity in entities
                )
            )


def show_recommendations(recommendations: list[dict]) -> None:
    st.header("Job Recommendations")
    if not recommendations:
        st.info(
            "No saved job listings are available yet. Analyze a job description "
            "first to add it to the database."
        )
        return

    for rank, recommendation in enumerate(recommendations, start=1):
        with st.container(border=True):
            title_col, score_col = st.columns([4, 1])
            title_col.subheader(f"{rank}. {recommendation['job_title']}")
            score_col.metric("Match", f"{recommendation['final_score']:.0f}%")
            st.progress(
                min(max(float(recommendation["final_score"]) / 100, 0), 1)
            )

            matched_col, missing_col = st.columns(2)
            with matched_col:
                st.markdown("**Matched**")
                st.write(", ".join(recommendation["matched_skills"]) or "None")
            with missing_col:
                st.markdown("**Missing**")
                st.write(", ".join(recommendation["missing_skills"]) or "None")
            st.caption(
                f"Semantic similarity: {recommendation['semantic_score']:.0f}%"
            )


st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1rem 1.15rem;
        border-radius: 0.85rem;
    }
    .skill-list {display: flex; flex-wrap: wrap; gap: 0.55rem;}
    .skill-badge {
        display: inline-block;
        padding: 0.38rem 0.72rem;
        border-radius: 999px;
        font-size: 0.92rem;
        font-weight: 600;
    }
    .skill-badge.matched {background: rgba(34, 197, 94, 0.14); color: #15803d;}
    .skill-badge.missing {background: rgba(239, 68, 68, 0.12); color: #b91c1c;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("📄 AI Resume Analyzer")
st.write("Upload a resume and compare it with a job description.")

try:
    skills_response = requests.get(f"{API_URL}/skills", timeout=5)
    skills_response.raise_for_status()
    skill_count = len(skills_response.json()["skills"])
    st.caption(f"API connected · {skill_count} searchable skills")
except requests.RequestException:
    st.warning("Backend API is unavailable. Start it with `uvicorn backend.main:app --reload`.")

user_name = st.text_input("Your name")
user_email = st.text_input("Your email")
uploaded_file = st.file_uploader("Resume PDF", type=["pdf"])

if st.button("Recommend jobs from database"):
    st.session_state.pop("recommendations", None)
    if not user_name.strip() or not user_email.strip():
        st.error("Enter your name and email to save and retrieve your analyses.")
    elif uploaded_file is None:
        st.error("Upload a resume PDF first.")
    else:
        try:
            with st.spinner("Comparing your resume with saved jobs..."):
                upload_response = requests.post(
                    f"{API_URL}/upload-resume",
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/pdf",
                        )
                    },
                    data={"name": user_name.strip(), "email": user_email.strip()},
                    timeout=30,
                )
                if not upload_response.ok:
                    st.error(request_error(upload_response))
                else:
                    resume_id = upload_response.json()["resume_id"]
                    response = requests.get(
                        f"{API_URL}/recommendations/{resume_id}",
                        timeout=300,
                    )
                    if response.ok:
                        st.session_state["recommendations"] = response.json()[
                            "recommendations"
                        ]
                    else:
                        st.error(request_error(response))
        except requests.RequestException as error:
            st.error(f"Could not reach the backend API: {error}")

job_title = st.text_input("Job title")
job_description = st.text_area("Job Description", height=220)

if st.button("Analyze Resume", type="primary"):
    st.session_state.pop("recommendations", None)
    if not user_name.strip() or not user_email.strip():
        st.error("Enter your name and email to save and retrieve your analyses.")
    elif uploaded_file is None:
        st.error("Upload a resume PDF first.")
    elif not job_title.strip():
        st.error("Enter a job title.")
    elif not job_description.strip():
        st.error("Enter a job description first.")
    else:
        try:
            with st.spinner("Uploading resume and analyzing match..."):
                upload_response = requests.post(
                    f"{API_URL}/upload-resume",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                    data={"name": user_name.strip(), "email": user_email.strip()},
                    timeout=30,
                )
                if not upload_response.ok:
                    st.error(request_error(upload_response))
                else:
                    resume_id = upload_response.json()["resume_id"]
                    analysis_response = requests.post(
                        f"{API_URL}/analyze",
                        json={
                            "resume_id": resume_id,
                            "job_title": job_title.strip(),
                            "job_description": job_description,
                        },
                        timeout=300,
                    )
                    if not analysis_response.ok:
                        st.error(request_error(analysis_response))
                    else:
                        analysis = analysis_response.json()
                        st.session_state["analysis_id"] = analysis["id"]
                        st.session_state["recommendations"] = analysis.get(
                            "recommendations",
                            [],
                        )
                        show_result(analysis["result"], uploaded_file.name)
        except requests.RequestException as error:
            st.error(f"Could not reach the backend API: {error}")

if "recommendations" in st.session_state:
    show_recommendations(st.session_state["recommendations"])

with st.expander("View my previous analyses"):
    if st.button("Load my history"):
        if not user_email.strip():
            st.error("Enter the email used when you uploaded your resume.")
        else:
            try:
                response = requests.get(
                    f"{API_URL}/history",
                    params={"email": user_email.strip()},
                    timeout=10,
                )
                if response.ok:
                    st.session_state["saved_analyses"] = response.json()["analyses"]
                else:
                    st.error(request_error(response))
            except requests.RequestException as error:
                st.error(f"Could not reach the backend API: {error}")

    saved_analyses = st.session_state.get("saved_analyses", [])
    if saved_analyses:
        selected_analysis_id = st.selectbox(
            "Saved analyses",
            options=[item["id"] for item in saved_analyses],
            format_func=lambda analysis_id: next(
                f"{item['job_title']} · {item['created_at']} · {item['final_score']:.1f}%"
                for item in saved_analyses
                if item["id"] == analysis_id
            ),
        )
        selected_analysis = next(
            item for item in saved_analyses if item["id"] == selected_analysis_id
        )
        st.caption(
            f"Resume: {selected_analysis['filename']} · "
            f"Job: {selected_analysis['job_title']}"
        )
        show_result(selected_analysis["result"], selected_analysis["filename"])
    elif "saved_analyses" in st.session_state:
        st.info("No saved analyses were found for this email.")

with st.expander("Retrieve a saved analysis"):
    analysis_id = st.text_input("Analysis ID", value=st.session_state.get("analysis_id", ""))
    if st.button("Load Analysis"):
        if not analysis_id.strip():
            st.error("Enter an analysis ID.")
        else:
            try:
                response = requests.get(f"{API_URL}/analysis/{analysis_id.strip()}", timeout=10)
                if response.ok:
                    saved_analysis = response.json()
                    show_result(
                        saved_analysis["result"],
                        saved_analysis.get("filename", "Saved resume"),
                    )
                else:
                    st.error(request_error(response))
            except requests.RequestException as error:
                st.error(f"Could not reach the backend API: {error}")