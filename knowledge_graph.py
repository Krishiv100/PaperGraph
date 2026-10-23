
# knowledge_graph.py
# Clean, research-oriented knowledge graph for PaperGraph

from collections import Counter
from html import escape
import re
import tempfile
from pathlib import Path

import networkx as nx
from pyvis.network import Network


# Restrained scientific color palette
COLORS = {
    "paper": "#263746",
    "problem": "#B77B27",
    "method": "#7566A8",
    "finding": "#28745F",
    "keyword": "#397CA5",
}

BACKGROUND = "#FFFFFF"
EDGE_COLOR = "#C8D1D9"
FONT_COLOR = "#263746"


def _clean_text(value):
    """Convert extracted content to readable text."""
    if value is None:
        return ""

    if isinstance(value, dict):
        for key in ("text", "content", "name", "title", "description"):
            if value.get(key):
                return _clean_text(value[key])
        return ""

    if isinstance(value, (list, tuple, set)):
        return " ".join(
            _clean_text(item) for item in value if item is not None
        ).strip()

    text = re.sub(r"\s+", " ", str(value)).strip()
    return text


def _get_first(data, keys, default=None):
    """Find the first available key in a dictionary."""
    if not isinstance(data, dict):
        return default

    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return default


def _as_list(value):
    """Normalize extracted results into a list."""
    if value is None:
        return []

    if isinstance(value, str):
        return [value] if value.strip() else []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, (list, tuple, set)):
        return list(value)

    return [value]


def _short_label(text, max_length=48):
    """Keep labels compact; the complete text remains in the tooltip."""
    text = _clean_text(text)

    if len(text) <= max_length:
        return text

    shortened = text[:max_length - 3].rsplit(" ", 1)[0]
    return (shortened or text[:max_length - 3]) + "..."


def _normalize_items(data, keys):
    """Extract a list of meaningful text items from analysis output."""
    raw = _get_first(data, keys, [])
    result = []

    for item in _as_list(raw):
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)

    return result


def _keyword_matches(keyword, text):
    """Match whole words rather than arbitrary character substrings."""
    keyword_words = re.findall(r"[a-z0-9]+", keyword.lower())
    text_words = set(re.findall(r"[a-z0-9]+", text.lower()))

    if not keyword_words:
        return False

    # Avoid weak links from very short keywords.
    if len(keyword_words) == 1 and len(keyword_words[0]) < 4:
        return False

    return all(word in text_words for word in keyword_words)


def build_knowledge_graph(analysis_results):
    """
    Build a clean knowledge graph from PaperGraph analysis output.

    Expected input is a dictionary containing a paper title and any of:
    problems, methods, findings, keywords.

    Common alternative field names are supported as well.
    """
    data = analysis_results if isinstance(analysis_results, dict) else {}

    graph = nx.Graph()

    title = _clean_text(
        _get_first(
            data,
            ["title", "paper_title", "document_title", "filename"],
            "Research Paper",
        )
    ) or "Research Paper"

    graph.add_node(
        "paper",
        label=_short_label(title, 54),
        title=escape(title),
        group="paper",
        color=COLORS["paper"],
        size=30,
        shape="box",
        font={"color": "#FFFFFF", "size": 17, "face": "Arial"},
    )

    categories = {
        "problem": _normalize_items(
            data, ["problems", "research_problems", "challenges"]
        ),
        "method": _normalize_items(
            data, ["methods", "methodologies", "approaches", "techniques"]
        ),
        "finding": _normalize_items(
            data, ["findings", "key_findings", "contributions", "results"]
        ),
        "keyword": _normalize_items(
            data, ["keywords", "keyphrases", "key_phrases"]
        ),
    }

    # Limit each group to keep the graph readable.
    limits = {
        "problem": 5,
        "method": 6,
        "finding": 5,
        "keyword": 8,
    }

    category_nodes = {}

    for category, items in categories.items():
        category_nodes[category] = []

        for index, text in enumerate(items[:limits[category]]):
            node_id = f"{category}_{index}"

            graph.add_node(
                node_id,
                label=_short_label(text, 34),
                title=escape(text),
                group=category,
                color=COLORS[category],
                size=17 if category != "keyword" else 12,
                shape="dot",
                font={"color": FONT_COLOR, "size": 12, "face": "Arial"},
            )

            category_nodes[category].append((node_id, text))

    # Connect extracted concepts to the paper.
    # These edges mean "extracted from this paper", not causal relations.
    for category in ("problem", "method", "finding"):
        for node_id, _ in category_nodes[category]:
            graph.add_edge(
                "paper",
                node_id,
                color=EDGE_COLOR,
                width=1.2,
                title="Extracted from paper",
                smooth=False,
            )

    # Connect keywords only when there is a clear textual match.
    # Keep each keyword's degree small to prevent a tangled graph.
    keyword_items = category_nodes["keyword"]

    for keyword_id, keyword_text in keyword_items:
        matched = []

        for category in ("problem", "method", "finding"):
            for node_id, text in category_nodes[category]:
                if _keyword_matches(keyword_text, text):
                    matched.append(node_id)

        # Only retain keyword nodes that have meaningful associations.
        for target_id in matched[:2]:
            graph.add_edge(
                keyword_id,
                target_id,
                color="#D9E0E6",
                width=0.8,
                dashes=True,
                title="Textual keyword association",
                smooth=False,
            )

    # Remove isolated keywords: they add clutter without context.
    for node_id, _ in keyword_items:
        if node_id in graph and graph.degree(node_id) == 0:
            graph.remove_node(node_id)

    return graph


def save_interactive_graph(graph):
    """
    Return interactive graph HTML for Streamlit components.html().

    Example:
        graph = build_knowledge_graph(analysis_results)
        graph_html = save_interactive_graph(graph)
    """
    net = Network(
        height="650px",
        width="100%",
        directed=False,
        bgcolor=BACKGROUND,
        font_color=FONT_COLOR,
        notebook=False,
        cdn_resources="in_line",
    )

    net.from_nx(graph)

    # Stable, restrained styling. Physics helps position nodes initially;
    # users can still drag nodes and zoom.
    net.set_options(
        """
        {
          "layout": {
            "improvedLayout": true
          },
          "nodes": {
            "borderWidth": 1,
            "borderWidthSelected": 2,
            "shadow": false,
            "font": {
              "face": "Arial",
              "size": 12",
              "strokeWidth": 0
            },
            "scaling": {
              "min": 10,
              "max": 25
            }
          },
          "edges": {
            "color": {
              "inherit": false,
              "color": "#C8D1D9",
              "highlight": "#718096"
            },
            "width": 1,
            "selectionWidth": 1,
            "hoverWidth": 1,
            "smooth": {
              "enabled": false
            }
          },
          "interaction": {
            "hover": true,
            "tooltipDelay": 180,
            "hideEdgesOnDrag": true,
            "navigationButtons": true,
            "keyboard": {
              "enabled": true
            }
          },
          "physics": {
            "enabled": true,
            "solver": "barnesHut",
            "barnesHut": {
              "gravitationalConstant": -4500,
              "centralGravity": 0.25,
              "springLength": 170,
              "springConstant": 0.025,
              "damping": 0.35,
              "avoidOverlap": 0.8
            },
            "stabilization": {
              "enabled": true,
              "iterations": 250,
              "updateInterval": 25,
              "fit": true
            },
            "minVelocity": 0.75
          }
        }
        """
    )

    # Write to a temporary HTML file, then return its contents to Streamlit.
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "papergraph.html"
        net.save_graph(str(output_path))
        return output_path.read_text(encoding="utf-8")
