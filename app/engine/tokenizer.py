from pythainlp import word_tokenize


def tokenize(text: str) -> list[str]:
    """
    Tokenize Thai text using PyThaiNLP's 'newmm' dictionary-based engine.
    Returns a list of non-empty, stripped tokens.
    """
    tokens = word_tokenize(text, engine="newmm", keep_whitespace=False)
    return [t.strip() for t in tokens if t.strip()]
