from functools import lru_cache

import pandas as pd
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

from analyzer.nlp import get_nlp


def load_skills(csv_path):

    df = pd.read_csv(csv_path)

    return df


def extract_skills(text, skills_df):
    skill_names = tuple(
        dict.fromkeys(
            str(skill).strip()
            for skill in skills_df["skill"]
            if pd.notna(skill) and str(skill).strip()
        )
    )
    if not skill_names:
        return []

    nlp = get_nlp()
    matcher = _get_skill_matcher(skill_names)
    skill_names_by_lower = {skill.casefold(): skill for skill in skill_names}
    doc = nlp.make_doc(text)
    spans = filter_spans(
        doc[start:end]
        for _, start, end in matcher(doc)
    )
    found_skills = {
        skill_names_by_lower[span.text.casefold()]
        for span in spans
        if span.text.casefold() in skill_names_by_lower
    }
    return sorted(found_skills)


@lru_cache(maxsize=8)
def _get_skill_matcher(skill_names):
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("SKILL", [nlp.make_doc(skill) for skill in skill_names])
    return matcher