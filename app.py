from pathlib import Path
import runpy


FRONTEND_APP = Path(__file__).resolve().parent / "frontend" / "app.py"
runpy.run_path(str(FRONTEND_APP), run_name="__main__")
from pathlib import Path

import streamlit as st  # type: ignore[reportMissingImports]

from analyzer.pdf_reader import (
    extract_text_from_pdf
)

from analyzer.text_cleaner import (
    clean_text
)

from analyzer.skill_extractor import (
    load_skills,
    extract_skills
)

from analyzer.matcher import (
    compare_skills
)

from analyzer.scorer import (
    calculate_skill_score,
    calculate_final_score,
    calculate_resume_quality
)

from analyzer.semantic_matcher import (
    calculate_semantic_similarity
)


BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
SKILLS_PATH = BASE_DIR / "data" / "skills.csv"


# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)


# -----------------------------
# TITLE
# -----------------------------

st.title(
    "📄 AI Resume Analyzer & Job Matcher"
)

st.write(
    "Upload your resume and compare it "
    "with a job description using NLP and "
    "semantic similarity."
)


# -----------------------------
# LOAD SKILLS
# -----------------------------

skills_df = load_skills(
    SKILLS_PATH
)


# -----------------------------
# RESUME UPLOAD
# -----------------------------

uploaded_file = st.file_uploader(
    "Upload Resume PDF",
    type=["pdf"]
)


# -----------------------------
# JOB DESCRIPTION
# -----------------------------

job_description = st.text_area(
    "Paste Job Description",
    height=250
)


# -----------------------------
# ANALYZE BUTTON
# -----------------------------

if st.button("🚀 Analyze Resume"):

    if uploaded_file is None:

        st.error(
            "Please upload a resume PDF."
        )

    elif not job_description.strip():

        st.error(
            "Please enter a job description."
        )

    else:

        # -------------------------
        # SAVE UPLOADED FILE
        # -------------------------

        pdf_path = UPLOADS_DIR / uploaded_file.name

        with open(
            pdf_path,
            "wb"
        ) as file:

            file.write(
                uploaded_file.getbuffer()
            )


        # -------------------------
        # EXTRACT RESUME TEXT
        # -------------------------

        resume_text = (
            extract_text_from_pdf(
                pdf_path
            )
        )


        # -------------------------
        # CLEAN TEXT
        # -------------------------

        cleaned_resume = (
            clean_text(resume_text)
        )

        cleaned_job = (
            clean_text(job_description)
        )


        # -------------------------
        # EXTRACT SKILLS
        # -------------------------

        resume_skills = (
            extract_skills(
                cleaned_resume,
                skills_df
            )
        )

        job_skills = (
            extract_skills(
                cleaned_job,
                skills_df
            )
        )


        # -------------------------
        # COMPARE SKILLS
        # -------------------------

        matched_skills, missing_skills = (
            compare_skills(
                resume_skills,
                job_skills
            )
        )


        # -------------------------
        # SKILL SCORE
        # -------------------------

        skill_score = (
            calculate_skill_score(
                matched_skills,
                job_skills
            )
        )


        # -------------------------
        # SEMANTIC SCORE
        # -------------------------

        semantic_score = (
            calculate_semantic_similarity(
                cleaned_resume,
                cleaned_job
            )
        )


        # -------------------------
        # FINAL SCORE
        # -------------------------

        final_score = (
            calculate_final_score(
                skill_score,
                semantic_score
            )
        )


        # -------------------------
        # RESUME QUALITY
        # -------------------------

        resume_quality = (
            calculate_resume_quality(
                cleaned_resume,
                resume_skills
            )
        )


        # =========================
        # RESULTS
        # =========================

        st.divider()

        st.header(
            "📊 Analysis Result"
        )


        # -------------------------
        # SCORE COLUMNS
        # -------------------------

        col1, col2, col3 = st.columns(3)


        with col1:

            st.metric(
                "Final Match",
                f"{final_score}%"
            )


        with col2:

            st.metric(
                "Skill Match",
                f"{skill_score}%"
            )


        with col3:

            st.metric(
                "Resume Quality",
                f"{resume_quality}%"
            )


        st.metric(
            "Semantic Similarity",
            f"{semantic_score}%"
        )


        st.divider()


        # -------------------------
        # MATCHED SKILLS
        # -------------------------

        st.subheader(
            "✅ Matched Skills"
        )

        if matched_skills:

            for skill in matched_skills:

                st.success(
                    skill.title()
                )

        else:

            st.warning(
                "No matching skills found."
            )


        # -------------------------
        # MISSING SKILLS
        # -------------------------

        st.subheader(
            "❌ Missing Skills"
        )

        if missing_skills:

            for skill in missing_skills:

                st.error(
                    skill.title()
                )

        else:

            st.success(
                "No major missing skills detected."
            )


        # -------------------------
        # RESUME SKILLS
        # -------------------------

        st.subheader(
            "🧠 Skills Found in Resume"
        )

        st.write(
            ", ".join(
                skill.title()
                for skill in resume_skills
            )
        )


        # -------------------------
        # JOB SKILLS
        # -------------------------

        st.subheader(
            "💼 Skills Required by Job"
        )

        st.write(
            ", ".join(
                skill.title()
                for skill in job_skills
            )
        )


        # -------------------------
        # RECOMMENDATIONS
        # -------------------------

        st.subheader(
            "💡 Recommendations"
        )

        if missing_skills:

            st.write(
                "Consider improving these skills:"
            )

            for skill in missing_skills:

                st.write(
                    f"→ Learn/practice {skill.title()}"
                )

        else:

            st.success(
                "Your detected skills cover "
                "the listed requirements."
            )


        # -------------------------
        # RAW TEXT
        # -------------------------

        with st.expander(
            "🔍 View Extracted Resume Text"
        ):

            st.write(resume_text)