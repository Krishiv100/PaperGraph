import re
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile

import networkx as nx
from pyvis.network import Network


def clean_label(text: str, max_words: int = 9) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    words = text.split()
    return " ".join(words[:max_words]) + ("…" if len(words) > max_words else "")


def _add_node(graph, node_id, label, title, color, size=20, shape="dot", group=None):
    graph.add_node(
        node_id,
        label=clean_label(label, 12),
        title=escape(str(title or label)),
        color=color,
        size=size,
        shape=shape,
        group=group or "concept",
        font={"size": 15, "face": "Arial", "color": "#172033", "strokeWidth": 3, "strokeColor": "#ffffff"},
        borderWidth=2,
    )


def build_knowledge_graph(paper_title: str, analysis: dict) -> nx.Graph:
    """Build an explorable graph from candidate insights and extracted keywords."""
    graph = nx.Graph()
    _add_node(graph, "paper", clean_label(paper_title or "Research paper", 10),
              paper_title or "Research paper", "#4f46e5", 34, "box", "paper")

    categories = [
        ("research_problem_candidates", "Problem", "#f59e0b"),
        ("method_candidates", "Method", "#8b5cf6"),
        ("result_candidates", "Finding", "#10b981"),
    ]
    concept_ids = []
    for key, category, color in categories:
        for index, sentence in enumerate((analysis.get(key) or [])[:3]):
            node_id = f"{category.lower()}_{index}"
            _add_node(graph, node_id, f"{category}: {clean_label(sentence, 8)}",
                      sentence, color, 22, "dot", category.lower())
            graph.add_edge("paper", node_id, label=f"candidate {category.lower()}",
                           color={"color": "#cbd5e1", "highlight": "#4f46e5"},
                           width=2, title=f"Candidate {category.lower()} associated with this paper")
            concept_ids.append(node_id)

    keyword_ids = []
    for index, keyword in enumerate((analysis.get("keywords") or [])[:10]):
        keyword = str(keyword).strip()
        if not keyword:
            continue
        node_id = f"keyword_{index}"
        _add_node(graph, node_id, keyword, f"Extracted keyword: {keyword}", "#06b6d4", 15, "dot", "keyword")
        graph.add_edge("paper", node_id, label="keyword", color={"color": "#dbeafe", "highlight": "#0891b2"},
                       width=1, title="Keyword extracted from the paper")
        keyword_ids.append(node_id)

    # Link each keyword to a candidate sentence only when the term literally appears there.
    candidate_texts = {}
    for key, _, _ in categories:
        candidate_texts.update({
            f"{key}_{i}": str(sentence).casefold()
            for i, sentence in enumerate((analysis.get(key) or [])[:3])
        })
    for ki, keyword in enumerate((analysis.get("keywords") or [])[:10]):
        term = str(keyword).casefold().strip()
        if len(term) < 3:
            continue
        for node_id, sentence in candidate_texts.items():
            if term in sentence:
                graph.add_edge(f"keyword_{ki}", node_id, label="mentioned in",
                               color={"color": "#94a3b8", "highlight": "#4f46e5"},
                               width=1, dashes=True, title="Keyword text appears in candidate sentence")

    # Ensure even sparse papers have a useful, honest graph rather than a blank canvas.
    if graph.number_of_nodes() == 1:
        _add_node(graph, "notice", "No concepts extracted", "The analysis returned no candidate insights or keywords.", "#94a3b8", 18)
        graph.add_edge("paper", "notice", label="analysis status", color="#cbd5e1", width=2)
    return graph


def save_interactive_graph(graph: nx.Graph, output_path: str | None = None) -> str:
    """Return standalone HTML; optionally write a copy to disk."""
    net = Network(
        height="640px",
        width="100%",
        directed=False,
        bgcolor="#fbfcff",
        font_color="#172033",
        cdn_resources="in_line",
        notebook=False,
        select_menu=True,
        filter_menu=True,
    )
    net.from_nx(graph)
    net.set_options("""
    {
      "nodes": {"borderWidth": 2, "shadow": {"enabled": true, "size": 8, "x": 0, "y": 3}},
      "edges": {"smooth": {"enabled": true, "type": "dynamic"}, "font": {"size": 10, "align": "middle", "background": "#ffffff"}, "color": {"inherit": false}},
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {"gravitationalConstant": -45, "centralGravity": 0.01, "springLength": 150, "springConstant": 0.08, "damping": 0.45, "avoidOverlap": 0.8},
        "stabilization": {"enabled": true, "iterations": 180, "fit": true}
      },
      "interaction": {"hover": true, "navigationButtons": true, "keyboard": true, "multiselect": true, "tooltipDelay": 120, "hideEdgesOnDrag": false, "zoomView": true}
    }
    """)
    html = net.generate_html()
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    return html
