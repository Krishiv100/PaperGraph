
import re
from pathlib import Path

import networkx as nx
from pyvis.network import Network


def clean_label(text: str, max_words: int = 7) -> str:
    """Create short, readable node labels."""
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()

    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."

    return text


def build_knowledge_graph(
    paper_title: str,
    analysis: dict,
) -> nx.Graph:
    """Build a small, readable graph for one research paper."""
    graph = nx.Graph()

    title = clean_label(paper_title or "Research Paper", 8)

    graph.add_node(
        "paper",
        label=title,
        title=title,
        color="#2563eb",
        size=35,
        shape="box",
        font={"size": 22},
    )

    # One representative sentence per category keeps the graph simple.
    categories = [
        ("research_problem_candidates", "Problem", "#f59e0b"),
        ("method_candidates", "Method", "#8b5cf6"),
        ("result_candidates", "Finding", "#10b981"),
    ]

    for key, label, color in categories:
        candidates = analysis.get(key, [])

        if not candidates:
            continue

        short_text = clean_label(candidates[0], 7)
        node_id = label.lower()

        graph.add_node(
            node_id,
            label=f"{label}\n{short_text}",
            title=candidates[0],
            color=color,
            size=23,
            shape="dot",
            font={"size": 16},
        )

        graph.add_edge(
            "paper",
            node_id,
            label="",
            color="#cbd5e1",
            width=2,
        )

    # Show at most three keywords as a single compact node.
    keywords = analysis.get("keywords", [])[:3]

    if keywords:
        keyword_text = ", ".join(
            clean_label(keyword, 3) for keyword in keywords
        )

        graph.add_node(
            "concepts",
            label=f"Key concepts\n{keyword_text}",
            title=keyword_text,
            color="#06b6d4",
            size=20,
            shape="dot",
            font={"size": 15},
        )

        graph.add_edge("paper", "concepts", color="#cbd5e1", width=2)

    return graph


def save_interactive_graph(
    graph: nx.Graph,
    output_path: str,
) -> None:
    """Save a compact interactive graph as UTF-8 HTML."""
    net = Network(
        height="500px",
        width="100%",
        directed=False,
        bgcolor="#ffffff",
        font_color="#1f2937",
        cdn_resources="in_line",
    )

    net.from_nx(graph)

    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -2500,
          "centralGravity": 0.25,
          "springLength": 160,
          "springConstant": 0.04,
          "damping": 0.2
        },
        "stabilization": {
          "iterations": 150
        }
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": true
      },
      "edges": {
        "smooth": false
      }
    }
    """)

    html = net.generate_html()

    Path(output_path).write_text(
        html,
        encoding="utf-8",
    )
