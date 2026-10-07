from functools import lru_cache

import spacy


@lru_cache(maxsize=1)
def get_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except OSError as error:
        raise RuntimeError(
            "The spaCy English model is missing. Install it with "
            "`python -m spacy download en_core_web_sm`."
        ) from error
