import re
from functools import lru_cache

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def load_models():
    """Cache the embedding and keyword models for the process lifetime."""
    model = SentenceTransformer(MODEL_NAME)
    return model, KeyBERT(model=model)


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    text = (text or "").strip()
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
    return [phrase for phrase, _score in keywords]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 30]


def rank_sentences(sentences: list[str], query: str, top_n: int = 3) -> list[str]:
    if not sentences:
        return []
    model, _ = load_models()
    candidates = sentences[:250]
    embeddings = model.encode([query] + candidates, normalize_embeddings=True, show_progress_bar=False)
    scores = embeddings[1:] @ embeddings[0]
    indices = scores.argsort()[::-1][:top_n]
    return [candidates[int(i)] for i in indices]


def analyze_paper(extraction: dict) -> dict:
    abstract = extraction.get("abstract", "")
    full_text = extraction.get("full_text", "")
    source_text = abstract if len(abstract) >= 50 else full_text
    keywords = extract_keywords(source_text)
    sentences = split_sentences(full_text)
    return {
        "keywords": keywords,
        "research_problem_candidates": rank_sentences(sentences, "What problem or research gap does this paper address?"),
        "method_candidates": rank_sentences(sentences, "What method, model, or approach does this paper propose?"),
        "result_candidates": rank_sentences(sentences, "What are the main experimental results or findings?"),
    }
