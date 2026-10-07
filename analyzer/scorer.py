def calculate_skill_score(
    matched_skills,
    required_skills
):

    if len(required_skills) == 0:

        return 0

    score = (
        len(matched_skills)
        / len(required_skills)
    ) * 100

    return round(score, 2)
def calculate_final_score(
    skill_score,
    semantic_score
):

    final_score = (
        skill_score * 0.70
        +
        semantic_score * 0.30
    )

    return round(final_score, 2)
def calculate_resume_quality(text, skills):

    score = 0

    text_lower = text.lower()

    # Skills
    if len(skills) >= 3:
        score += 20

    # Education
    if "education" in text_lower:
        score += 15

    # Projects
    if "project" in text_lower:
        score += 20

    # Experience
    if "experience" in text_lower:
        score += 20

    # Certification
    if "certification" in text_lower:
        score += 10

    # Contact
    if "@" in text:
        score += 15

    return min(score, 100)