def compare_skills(resume_skills, job_skills):

    resume_set = set(
        skill.lower()
        for skill in resume_skills
    )

    job_set = set(
        skill.lower()
        for skill in job_skills
    )

    matched = resume_set.intersection(job_set)

    missing = job_set.difference(resume_set)

    return sorted(matched), sorted(missing)