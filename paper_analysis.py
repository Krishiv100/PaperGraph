
import re

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer


# Small, open-source embedding model.
# It downloads on first use and runs locally afterward.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_keyword_model = None


def load_models():
    """Load models once, then reuse them for later papers."""
    global _model, _keyword_model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
        _keyword_model = KeyBERT(model=_model)

    return _model, _keyword_model


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract representative keywords from a paper."""
    text = text.strip()

    if len(text) < 50:
        return []

    _, keyword_model = load_models()

    keywords = keyword_model.extract_keywords(
        text[:20000],
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        top_n=top_n,
        use_mmr=True,
        diversity=0.5,
    )

    return [phrase for phrase, score in keywords]


def split_sentences(text: str) -> list[str]:
    """Split extracted text into approximate sentences."""
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if len(sentence.strip()) > 30
    ]


def rank_sentences(
    sentences: list[str],
    query: str,
    top_n: int = 3,
) -> list[str]:
    """Rank sentences by semantic similarity to a research question."""
    if not sentences:
        return []

    model, _ = load_models()

    # Limit work on unusually long papers.
    candidates = sentences[:250]
    embeddings = model.encode(
        [query] + candidates,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    query_embedding = embeddings[0]
    sentence_embeddings = embeddings[1:]

    scores = sentence_embeddings @ query_embedding
    ranked_indices = scores.argsort()[::-1][:top_n]

    return [
        candidates[int(index)]
        for index in ranked_indices
    ]


def analyze_paper(extraction: dict) -> dict:
    """Generate a first-pass NLP analysis from extracted PDF text."""
    abstract = extraction.get("abstract", "")
    full_text = extraction.get("full_text", "")

    # Prefer the abstract for keywords; use the full text as fallback.
    source_text = abstract if len(abstract) >= 50 else full_text

    keywords = extract_keywords(source_text)
    sentences = split_sentences(full_text)

    return {
        "keywords": keywords,
        "research_problem_candidates": rank_sentences(
            sentences,
            "What problem or research gap does this paper address?",
        ),
        "method_candidates": rank_sentences(
            sentences,
            "What method, model, or approach does this paper propose?",
        ),
        "result_candidates": rank_sentences(
            sentences,
            "What are the main experimental results or findings?",
        ),
    }
