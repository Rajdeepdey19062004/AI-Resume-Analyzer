from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@lru_cache(maxsize=1)
def _load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


def calculate_semantic_similarity(
    resume_text,
    job_description
):

    model = _load_model()

    resume_embedding = model.encode(
        resume_text
    )

    job_embedding = model.encode(
        job_description
    )

    similarity = cosine_similarity(
        [resume_embedding],
        [job_embedding]
    )[0][0]

    score = similarity * 100

    return round(score, 2)


def calculate_semantic_similarities(resume_text, job_descriptions):
    if not job_descriptions:
        return []

    model = _load_model()
    embeddings = model.encode([resume_text, *job_descriptions])
    similarities = cosine_similarity(
        [embeddings[0]],
        embeddings[1:],
    )[0]
    return [round(float(similarity) * 100, 2) for similarity in similarities]