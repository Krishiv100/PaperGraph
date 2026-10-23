"""
paper_analysis.py
NLP analysis engine for PaperGraph.

Provides:
  - Keyword extraction (KeyBERT)
  - Sentence ranking for research problems / methods / findings
  - Summary cards (core claim, contributions, limitations)
  - Concept flashcards (keyword → best explanatory sentence)
  - Reading stats (readability, estimated time, jargon density)
  - Methodology flow (ordered step list for flowchart)
"""

import re
from functools import lru_cache

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def load_models():
    """Cache the embedding and keyword models for the process lifetime."""
    model = SentenceTransformer(MODEL_NAME)
    return model, KeyBERT(model=model)


# ---------------------------------------------------------------------------
# Core NLP helpers
# ---------------------------------------------------------------------------

def extract_keywords(text: str, top_n: int = 12) -> list[str]:
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
    embeddings = model.encode(
        [query] + candidates, normalize_embeddings=True, show_progress_bar=False
    )
    scores = embeddings[1:] @ embeddings[0]
    indices = scores.argsort()[::-1][:top_n]
    return [candidates[int(i)] for i in indices]


# ---------------------------------------------------------------------------
# Summary cards
# ---------------------------------------------------------------------------

def generate_summary_cards(sentences: list[str], abstract: str) -> dict:
    """
    Extract structured summary information from the paper text.
    Returns a dict with core_claim, contributions, limitations, future_work.
    """
    queries = {
        "core_claim": (
            "What is the main claim, thesis, or central argument of this paper?",
            1,
        ),
        "contributions": (
            "What are the key contributions or novel aspects of this research?",
            3,
        ),
        "limitations": (
            "What are the limitations, weaknesses, or constraints of this work?",
            2,
        ),
        "future_work": (
            "What future work, directions, or open problems does the paper suggest?",
            2,
        ),
    }

    # For core claim, prefer the abstract if available
    abstract_sentences = split_sentences(abstract) if abstract else []
    source = abstract_sentences + sentences if abstract_sentences else sentences

    cards = {}
    for key, (query, top_n) in queries.items():
        src = abstract_sentences if key == "core_claim" and abstract_sentences else source
        results = rank_sentences(src, query, top_n=top_n)
        cards[key] = results

    return cards


# ---------------------------------------------------------------------------
# Concept flashcards
# ---------------------------------------------------------------------------

def generate_flashcards(sentences: list[str], keywords: list[str]) -> list[dict]:
    """
    For each keyword, find the most relevant explanatory sentence.
    Returns a list of {'term': str, 'explanation': str} dicts.
    """
    if not sentences or not keywords:
        return []

    model, _ = load_models()
    # Encode all sentences once
    sent_embeddings = model.encode(sentences[:300], normalize_embeddings=True, show_progress_bar=False)

    flashcards = []
    seen_explanations: set[str] = set()

    for keyword in keywords[:12]:
        query_emb = model.encode(
            [f"What is {keyword}? Define or explain {keyword} in this research context."],
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        scores = sent_embeddings @ query_emb
        best_idx = int(scores.argmax())
        explanation = sentences[best_idx]

        # Skip near-duplicates
        if explanation in seen_explanations:
            continue
        seen_explanations.add(explanation)

        flashcards.append({"term": keyword, "explanation": explanation})

    return flashcards


# ---------------------------------------------------------------------------
# Reading stats
# ---------------------------------------------------------------------------

def compute_reading_stats(full_text: str, page_count: int) -> dict:
    """
    Compute readability metrics and reading time for the paper.
    Falls back to basic estimates if textstat is unavailable.
    """
    word_count = len(re.findall(r"\b\w+\b", full_text or ""))
    char_count = len(full_text or "")

    # Estimated reading time at 200 words per minute (academic reading pace)
    reading_minutes = max(1, round(word_count / 200))

    # Jargon density: ratio of long technical words (>= 8 chars) to all words
    long_words = re.findall(r"\b[A-Za-z]{8,}\b", full_text or "")
    jargon_pct = round(len(long_words) / max(1, word_count) * 100, 1)

    # Citation estimate: count patterns like "[1]", "(Author, 2020)", etc.
    citation_count = len(
        re.findall(
            r"\[\d+\]|\(\w[\w\s,]+,\s*\d{4}[a-z]?\)",
            full_text or "",
        )
    )

    # Readability via textstat
    flesch_score = None
    grade_level = None
    difficulty_label = "Unknown"

    try:
        import textstat

        sample = (full_text or "")[:15000]  # textstat works best on manageable text
        flesch_score = round(textstat.flesch_reading_ease(sample), 1)
        grade_level = round(textstat.flesch_kincaid_grade(sample), 1)

        if flesch_score >= 60:
            difficulty_label = "Accessible"
        elif flesch_score >= 30:
            difficulty_label = "Academic"
        else:
            difficulty_label = "Highly Technical"

    except ImportError:
        # Fallback estimate based on average word length
        avg_word_len = char_count / max(1, word_count)
        if avg_word_len < 5:
            difficulty_label = "Accessible"
        elif avg_word_len < 6.5:
            difficulty_label = "Academic"
        else:
            difficulty_label = "Highly Technical"

    return {
        "word_count": word_count,
        "reading_minutes": reading_minutes,
        "jargon_pct": jargon_pct,
        "citation_count": citation_count,
        "flesch_score": flesch_score,
        "grade_level": grade_level,
        "difficulty_label": difficulty_label,
        "page_count": page_count,
    }


# ---------------------------------------------------------------------------
# Methodology flow
# ---------------------------------------------------------------------------

# Phrases that signal ordered method steps
_STEP_PATTERNS = [
    re.compile(r"^(?:step\s+\d+|phase\s+\d+|\d+\.\s)[\s:\-–]+(.+)", re.I),
    re.compile(r"^(?:first(?:ly)?|second(?:ly)?|third(?:ly)?|fourth(?:ly)?|finally|subsequently|thereafter|next|then),?\s+(.+)", re.I),
    re.compile(r"^we\s+(?:first|then|next|subsequently|finally)\s+(.+)", re.I),
]

_METHOD_KEYWORDS = [
    "collect", "preprocess", "train", "evaluate", "test", "deploy",
    "extract", "classify", "cluster", "fine-tune", "generate", "detect",
    "annotate", "sample", "filter", "tokenize", "embed", "encode",
    "validate", "measure", "compute", "estimate", "optimize", "rank",
]


def extract_methodology_flow(sentences: list[str], method_candidates: list[str]) -> list[str]:
    """
    Return an ordered list of concise method steps for the flowchart.
    Uses pattern matching first, then semantic ranking as fallback.
    """
    steps: list[str] = []

    # Pass 1: explicit step patterns
    for sentence in sentences[:500]:
        for pattern in _STEP_PATTERNS:
            m = pattern.match(sentence.strip())
            if m:
                step_text = m.group(1).strip()
                if 20 < len(step_text) < 200 and step_text not in steps:
                    steps.append(step_text)
                break

    # Pass 2: sentences mentioning method verbs if we have few steps
    if len(steps) < 4:
        for sentence in sentences[:300]:
            lower = sentence.lower()
            if any(kw in lower for kw in _METHOD_KEYWORDS):
                cleaned = sentence.strip()
                if 30 < len(cleaned) < 180 and cleaned not in steps:
                    steps.append(cleaned)
                if len(steps) >= 8:
                    break

    # Pass 3: fall back to method_candidates
    if len(steps) < 3:
        for mc in method_candidates:
            cleaned = mc.strip()
            if cleaned and cleaned not in steps:
                steps.append(cleaned)

    # Trim to a readable pipeline length, and shorten each step
    trimmed = []
    for step in steps[:8]:
        # Keep first ~100 chars cleanly
        if len(step) > 110:
            step = step[:107].rsplit(" ", 1)[0] + "…"
        trimmed.append(step)

    return trimmed


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_paper(extraction: dict) -> dict:
    """
    Run all NLP analyses on the extracted paper data.
    Returns a unified dict consumed by app.py and knowledge_graph.py.
    """
    abstract = extraction.get("abstract", "")
    full_text = extraction.get("full_text", "")
    page_count = extraction.get("page_count", 0)

    source_text = abstract if len(abstract) >= 50 else full_text

    keywords = extract_keywords(source_text)
    sentences = split_sentences(full_text)

    research_problem_candidates = rank_sentences(
        sentences, "What problem or research gap does this paper address?"
    )
    method_candidates = rank_sentences(
        sentences, "What method, model, or approach does this paper propose?"
    )
    result_candidates = rank_sentences(
        sentences, "What are the main experimental results or findings?"
    )

    summary_cards = generate_summary_cards(sentences, abstract)
    flashcards = generate_flashcards(sentences, keywords)
    reading_stats = compute_reading_stats(full_text, page_count)
    methodology_flow = extract_methodology_flow(sentences, method_candidates)

    return {
        # Existing fields (kept for backward compat)
        "keywords": keywords,
        "research_problem_candidates": research_problem_candidates,
        "method_candidates": method_candidates,
        "result_candidates": result_candidates,
        # New fields
        "summary_cards": summary_cards,
        "flashcards": flashcards,
        "reading_stats": reading_stats,
        "methodology_flow": methodology_flow,
    }
