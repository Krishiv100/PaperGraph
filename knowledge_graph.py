
import html
import json
import re
from pathlib import Path

import networkx as nx
from pyvis.network import Network


# Restrained colors chosen to distinguish research entity types.

COLORS = {
    "paper": "#263746",   # Core paper
    "problem": "#B77B27", # Research problem
    "method": "#7566A8",  # Methodology
    "finding": "#28745F", # Findings
    "keyword": "#397CA5", # Keywords
    "notice": "#788692",  # Empty or unavailable information
}

CATEGORIES = [
    ("research_problem_candidates", "problem", "Research problem"),
    ("method_candidates", "method", "Method"),
    ("result_candidates", "finding", "Finding"),
]


def clean_label(text: str, max_words: int = 8) -> str:
    """Create a compact label while preserving the full text elsewhere."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    words = text.split()

    if len(words) > max_words:
        return " ".join(words[:max_words]) + "…"

    return text


def _add_node(
    graph: nx.Graph,
    node_id: str,
    label: str,
    description: str,
    category: str,
    size: int = 20,
    shape: str = "dot",
) -> None:
    """Add a graph node with a short label and a full-text tooltip."""
    graph.add_node(
        node_id,
        label=clean_label(label),
        title=html.escape(str(description or label)),
        color=COLORS.get(category, COLORS["notice"]),
        size=size,
        shape=shape,
        group=category,
        font={
            "face": "Arial",
            "size": 16,
            "color": "#263746",
            "strokeWidth": 3,
            "strokeColor": "#ffffff",
        },
        borderWidth=1.5,
    )


def _normalise_terms(text: str) -> set[str]:
    """Extract words and short phrases for conservative text matching."""
    text = str(text or "").casefold()
    return set(re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", text))


def _keyword_matches(keyword: str, sentence: str) -> bool:
    """
    Match a keyword as a complete phrase or sequence of tokens.
    This avoids false matches such as 'net' matching 'network'.
    """
    keyword_tokens = re.findall(
        r"[a-z0-9]+(?:[-'][a-z0-9]+)*",
        str(keyword or "").casefold(),
    )
    sentence_tokens = re.findall(
        r"[a-z0-9]+(?:[-'][a-z0-9]+)*",
        str(sentence or "").casefold(),
    )

    if not keyword_tokens or not sentence_tokens:
        return False

    width = len(keyword_tokens)

    return any(
        sentence_tokens[i:i + width] == keyword_tokens
        for i in range(len(sentence_tokens) - width + 1)
    )


def build_knowledge_graph(paper_title: str, analysis: dict) -> nx.Graph:
    """
    Build a research-paper graph from extracted candidate insights and keywords.

    Edges represent:
    - paper -> extracted problem, method, or finding
    - paper -> extracted keyword
    - keyword -> candidate passage when its wording matches that passage

    These are textual associations, not independently verified scientific claims.
    """
    analysis = analysis or {}
    graph = nx.Graph()

    title = str(paper_title or "Research paper").strip()
    _add_node(
        graph,
        "paper",
        clean_label(title, 9),
        title,
        "paper",
        size=32,
        shape="box",
    )

    # Store the actual graph node IDs alongside their source text.
    candidate_nodes = []

    for source_key, category, display_name in CATEGORIES:
        candidates = analysis.get(source_key) or []

        if isinstance(candidates, str):
            candidates = [candidates]

        for index, sentence in enumerate(candidates[:4]):
            sentence = str(sentence or "").strip()

            if not sentence:
                continue

            node_id = f"{category}_{index}"

            _add_node(
                graph,
                node_id,
                sentence,
                f"{display_name}\n\n{sentence}",
                category,
                size=23,
            )

            graph.add_edge(
                "paper",
                node_id,
                relation="contains_candidate",
                label=display_name.lower(),
                color="#c6d0d9",
                width=1.5,
                title=(
                    f"Candidate {display_name.lower()} extracted "
                    "from this paper"
                ),
            )

            candidate_nodes.append((node_id, sentence, category))

    # Add unique keyword nodes.
    keywords = analysis.get("keywords") or []

    if isinstance(keywords, str):
        keywords = [keywords]

    keyword_nodes = []
    seen_keywords = set()

    for index, keyword in enumerate(keywords):
        keyword = re.sub(r"\s+", " ", str(keyword or "")).strip()
        normalised = keyword.casefold()

        if not keyword or normalised in seen_keywords:
            continue

        seen_keywords.add(normalised)

        node_id = f"keyword_{index}"

        _add_node(
            graph,
            node_id,
            keyword,
            f"Extracted keyword\n\n{keyword}",
            "keyword",
            size=17,
        )

        graph.add_edge(
            "paper",
            node_id,
            relation="has_keyword",
            label="keyword",
            color="#d5e1e9",
            width=1,
            title="Keyword returned by the paper-analysis pipeline",
        )

        keyword_nodes.append((node_id, keyword))

    # Link keywords to candidate passages only when their wording matches.
    # Fixes the previous node-ID mismatch.
    for keyword_id, keyword in keyword_nodes:
        for candidate_id, sentence, _category in candidate_nodes:
            if _keyword_matches(keyword, sentence):
                graph.add_edge(
                    keyword_id,
                    candidate_id,
                    relation="textual_match",
                    label="text match",
                    color="#9aabb8",
                    width=1.2,
                    dashes=True,
                    title=(
                        "The keyword phrase appears in the candidate text. "
                        "This indicates textual overlap, not causal evidence."
                    ),
                )

    # Handle empty or very sparse analyses without a misleading blank graph.
    if graph.number_of_nodes() == 1:
        _add_node(
            graph,
            "notice",
            "No concepts extracted",
            (
                "The current analysis returned no usable candidate insights "
                "or keywords. Check the extracted PDF text and analysis output."
            ),
            "notice",
            size=18,
        )

        graph.add_edge(
            "paper",
            "notice",
            relation="analysis_status",
            label="analysis status",
            color="#c6d0d9",
            width=1.5,
        )

    graph.graph["description"] = (
        "Relationships are derived from extracted candidate text and keywords. "
        "They should be reviewed against the source paper."
    )

    return graph


def save_interactive_graph(
    graph: nx.Graph,
    output_path: str | None = None,
) -> str:
    """Return interactive, self-contained PyVis HTML and optionally save it."""
    
    net = Network(
        height="640px",
        width="100%",
        directed=False,
        bgcolor="#FFFFFF",
        font_color="#263746",
        cdn_resources="in_line",
        notebook=False,
    )


    net.from_nx(graph)

    options = {
        "autoResize": True,
        "nodes": {
            "borderWidth": 1.5,
            "borderWidthSelected": 2.5,
            "shapeProperties": {"borderRadius": 4},
            "scaling": {"min": 14, "max": 32},
            "shadow": False,
        },
        
        "edges": {
            "smooth": {"enabled": True, "type": "continuous"},
            "color": {
                "inherit": False,
                "color": "#C8D2D9",
                "highlight": "#356F70",
                "hover": "#637F8C",
            },
            "font": {
                "size": 10,
                "face": "Arial",
                "color": "#526575",
                "background": "#FFFFFF",
                "strokeWidth": 0,
            },
        },

        "physics": {
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -65,
                "centralGravity": 0.012,
                "springLength": 145,
                "springConstant": 0.07,
                "damping": 0.5,
                "avoidOverlap": 0.8,
            },
            "stabilization": {
                "enabled": True,
                "iterations": 200,
                "fit": True,
            },
        },
        "interaction": {
            "hover": True,
            "tooltipDelay": 150,
            "navigationButtons": True,
            "keyboard": {"enabled": True},
            "multiselect": True,
            "selectConnectedEdges": True,
            "hideEdgesOnDrag": True,
            "zoomView": True,
        },
    }

    net.set_options(json.dumps(options))
    generated_html = net.generate_html()

    if not generated_html or "vis-network" not in generated_html:
        raise RuntimeError("PyVis did not generate a valid interactive graph.")

    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated_html, encoding="utf-8")

    return generated_html
