import re
from functools import lru_cache

from spacy.matcher import Matcher, PhraseMatcher

from analyzer.nlp import get_nlp
from analyzer.skill_extractor import extract_skills


ROLE_TERMS = (
    "Python Developer",
    "Software Developer",
    "Software Engineer",
    "Data Scientist",
    "Data Analyst",
    "Machine Learning Engineer",
    "AI Engineer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "Web Developer",
    "DevOps Engineer",
    "Cloud Engineer",
    "QA Engineer",
    "Project Manager",
    "Business Analyst",
    "Product Manager",
    "Systems Administrator",
)

EDUCATION_TERMS = {
    "Associate degree": (
        "associate degree",
        "associate's degree",
    ),
    "Bachelor's degree": (
        "bachelor's degree",
        "bachelor degree",
        "bachelor of science",
        "bachelor of arts",
        "bsc",
        "b.sc.",
        "b.s.",
        "b.a.",
    ),
    "Master's degree": (
        "master's degree",
        "master degree",
        "master of science",
        "master of arts",
        "msc",
        "m.sc.",
        "m.s.",
        "m.a.",
        "mba",
    ),
    "Doctorate": (
        "phd",
        "ph.d.",
        "doctorate",
        "doctoral degree",
    ),
    "Diploma": ("diploma",),
    "High school": ("high school diploma",),
}

EXPERIENCE_PATTERN = re.compile(
    r"(?<!\w)(?P<value>\d+(?:\.\d+)?)\s*\+?\s*"
    r"(?P<unit>years?|yrs?|months?|mos?)(?!\w)",
    re.IGNORECASE,
)

EDUCATION_CONTEXT = re.compile(
    r"\b(education|graduat(?:e|ed|ion)|studied|degree|university|"
    r"college|institute|school)\b",
    re.IGNORECASE,
)
INSTITUTION_NAME = re.compile(
    r"\b(university|college|institute|school|academy|polytechnic)\b",
    re.IGNORECASE,
)
INSTITUTION_INTRODUCER = re.compile(r"\b(?:at|from)\s+(?:the\s+)?$", re.IGNORECASE)


def extract_resume_profile(text, skills_df):
    nlp = get_nlp()
    doc = nlp(text)

    roles = _extract_roles(doc)
    degrees = _extract_degrees(doc)
    entities = [
        {"text": entity.text, "label": entity.label_}
        for entity in doc.ents
        if entity.label_ in {"PERSON", "ORG", "GPE", "LOC", "FAC", "DATE"}
    ]
    institutions = _extract_education_institutions(doc)

    return {
        "role": roles,
        "experience": _extract_experience(text),
        "education": {
            "degrees": degrees,
            "institutions": institutions,
        },
        "entities": entities,
        "skills": extract_skills(text, skills_df),
    }


def _extract_roles(doc):
    matcher = _get_role_matcher()
    role_lookup = {role.casefold(): role for role in ROLE_TERMS}
    roles = {
        role_lookup[doc[start:end].text.casefold()]
        for _, start, end in matcher(doc)
    }

    contextual_matcher = _get_contextual_role_matcher()
    for _, start, end in contextual_matcher(doc):
        role = doc[start:end].text.strip(" ,.;:")
        if role:
            roles.add(role)

    return sorted(roles, key=str.casefold)


def _extract_degrees(doc):
    matcher = _get_education_matcher()
    found = set()
    for match_id, start, end in matcher(doc):
        label = doc.vocab.strings[match_id]
        found.add(label)
    return sorted(found)


def _extract_experience(text):
    experiences = []
    seen = set()
    for match in EXPERIENCE_PATTERN.finditer(text):
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        if unit.startswith(("month", "mo")):
            years = value / 12
            duration = f"{match.group('value')} months"
        else:
            years = value
            duration = f"{match.group('value')} years"
        key = (years, duration)
        if key not in seen:
            experiences.append({"duration": duration, "years": years})
            seen.add(key)
    return experiences


def _extract_education_institutions(doc):
    institutions = set()
    for sentence in doc.sents:
        if EDUCATION_CONTEXT.search(sentence.text):
            for entity in sentence.ents:
                if entity.label_ != "ORG":
                    continue
                prefix = sentence.text[: entity.start_char - sentence.start_char]
                if not (
                    INSTITUTION_NAME.search(entity.text)
                    or INSTITUTION_INTRODUCER.search(prefix)
                ):
                    continue
                institutions.add(re.sub(r"^the\s+", "", entity.text, flags=re.I))
    return sorted(institutions, key=str.casefold)


@lru_cache(maxsize=1)
def _get_role_matcher():
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    matcher.add("ROLE", [nlp.make_doc(role) for role in ROLE_TERMS])
    return matcher


@lru_cache(maxsize=1)
def _get_contextual_role_matcher():
    matcher = Matcher(get_nlp().vocab)
    matcher.add(
        "ROLE_AFTER_AS",
        [
            [
                {"LEMMA": {"IN": ["work", "serve", "join"]}},
                {"LOWER": "as"},
                {"POS": "DET", "OP": "?"},
                {"POS": {"IN": ["ADJ", "NOUN", "PROPN"]}, "OP": "+"},
            ]
        ],
    )
    return matcher


@lru_cache(maxsize=1)
def _get_education_matcher():
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for label, aliases in EDUCATION_TERMS.items():
        matcher.add(label, [nlp.make_doc(alias) for alias in aliases])
    return matcher
