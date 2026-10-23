"""
knowledge_graph.py
Graph and mind-map generation for PaperGraph.

Exports:
  build_knowledge_graph(analysis_results)  → networkx.Graph
  save_interactive_graph(graph)            → HTML string (pyvis network)
  build_mind_map_html(title, analysis)     → HTML string (D3.js radial tree)
"""

import json
import re
import tempfile
from html import escape
from pathlib import Path

import networkx as nx
from pyvis.network import Network


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

COLORS = {
    "paper":   "#263746",
    "problem": "#B77B27",
    "method":  "#7566A8",
    "finding": "#28745F",
    "keyword": "#397CA5",
}

BACKGROUND  = "#FFFFFF"
EDGE_COLOR  = "#C8D1D9"
FONT_COLOR  = "#263746"

# Mind-map branch colours (one per category)
MM_COLORS = {
    "Abstract":      "#5B8FF9",
    "Core Claim":    "#F6BD16",
    "Methods":       "#7566A8",
    "Findings":      "#28745F",
    "Contributions": "#E8684A",
    "Limitations":   "#9270CA",
    "Keywords":      "#397CA5",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
        return " ".join(_clean_text(item) for item in value if item is not None).strip()
    return re.sub(r"\s+", " ", str(value)).strip()


def _get_first(data, keys, default=None):
    if not isinstance(data, dict):
        return default
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def _as_list(value):
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
    text = _clean_text(text)
    if len(text) <= max_length:
        return text
    shortened = text[:max_length - 3].rsplit(" ", 1)[0]
    return (shortened or text[:max_length - 3]) + "..."


def _normalize_items(data, keys):
    raw = _get_first(data, keys, [])
    result = []
    for item in _as_list(raw):
        text = _clean_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _keyword_matches(keyword, text):
    keyword_words = re.findall(r"[a-z0-9]+", keyword.lower())
    text_words = set(re.findall(r"[a-z0-9]+", text.lower()))
    if not keyword_words:
        return False
    if len(keyword_words) == 1 and len(keyword_words[0]) < 4:
        return False
    return all(word in text_words for word in keyword_words)


def _truncate(text: str, n: int = 80) -> str:
    """Shorten text for mind-map node labels."""
    text = _clean_text(text)
    if len(text) <= n:
        return text
    return text[:n - 1].rsplit(" ", 1)[0] + "…"


# ---------------------------------------------------------------------------
# Knowledge graph (pyvis network)
# ---------------------------------------------------------------------------

def build_knowledge_graph(analysis_results):
    """
    Build a clean knowledge graph from PaperGraph analysis output.

    ``analysis_results`` is the dict returned by ``paper_analysis.analyze_paper``.
    It must contain at minimum a ``title`` field plus any of:
    problems, methods, findings, keywords.
    """
    data = analysis_results if isinstance(analysis_results, dict) else {}

    graph = nx.Graph()

    title = _clean_text(
        _get_first(data, ["title", "paper_title", "document_title", "filename"], "Research Paper")
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
        "problem": _normalize_items(data, ["research_problem_candidates", "problems", "research_problems", "challenges"]),
        "method":  _normalize_items(data, ["method_candidates", "methods", "methodologies", "approaches", "techniques"]),
        "finding": _normalize_items(data, ["result_candidates", "findings", "key_findings", "contributions", "results"]),
        "keyword": _normalize_items(data, ["keywords", "keyphrases", "key_phrases"]),
    }

    limits = {"problem": 5, "method": 6, "finding": 5, "keyword": 8}
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

    for category in ("problem", "method", "finding"):
        for node_id, _ in category_nodes[category]:
            graph.add_edge("paper", node_id, color=EDGE_COLOR, width=1.2,
                           title="Extracted from paper", smooth=False)

    keyword_items = category_nodes["keyword"]
    for keyword_id, keyword_text in keyword_items:
        matched = []
        for category in ("problem", "method", "finding"):
            for node_id, text in category_nodes[category]:
                if _keyword_matches(keyword_text, text):
                    matched.append(node_id)
        for target_id in matched[:2]:
            graph.add_edge(keyword_id, target_id, color="#D9E0E6", width=0.8,
                           dashes=True, title="Textual keyword association", smooth=False)

    for node_id, _ in keyword_items:
        if node_id in graph and graph.degree(node_id) == 0:
            graph.remove_node(node_id)

    return graph


def save_interactive_graph(graph):
    """Return interactive graph HTML for Streamlit components.html()."""
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
    net.set_options("""
    {
      "layout": { "improvedLayout": true },
      "nodes": {
        "borderWidth": 1,
        "borderWidthSelected": 2,
        "shadow": false,
        "font": { "face": "Arial", "size": 12, "strokeWidth": 0 },
        "scaling": { "min": 10, "max": 25 }
      },
      "edges": {
        "color": { "inherit": false, "color": "#C8D1D9", "highlight": "#718096" },
        "width": 1,
        "selectionWidth": 1,
        "hoverWidth": 1,
        "smooth": { "enabled": false }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 180,
        "hideEdgesOnDrag": true,
        "navigationButtons": true,
        "keyboard": { "enabled": true }
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
    """)
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "papergraph.html"
        net.save_graph(str(output_path))
        return output_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Mind map (D3.js radial tree)
# ---------------------------------------------------------------------------

def build_mind_map_html(title: str, analysis: dict) -> str:
    """
    Return a self-contained HTML string with an interactive D3.js radial
    mind-map for the given paper.

    The tree has:
      root → branches (Abstract, Core Claim, Methods, Findings,
                        Contributions, Limitations, Keywords)
           → leaf nodes (extracted text snippets)
    """

    def _leaves(keys, max_items=5):
        for k in keys:
            raw = analysis.get(k)
            if raw:
                items = raw if isinstance(raw, list) else [raw]
                out = []
                for item in items[:max_items]:
                    if isinstance(item, dict):
                        item = item.get("explanation") or item.get("term") or str(item)
                    t = _truncate(str(item), 70)
                    if t:
                        out.append(t)
                return out
        return []

    abstract_text = analysis.get("abstract", "") or ""
    abstract_leaves = (
        [_truncate(abstract_text, 70)] if abstract_text else ["No abstract detected"]
    )

    # Build the tree structure as plain Python dicts, then JSON-encode
    summary = analysis.get("summary_cards", {})
    tree = {
        "name": _truncate(title, 60),
        "type": "root",
        "children": [
            {
                "name": "Abstract",
                "type": "branch",
                "color": MM_COLORS["Abstract"],
                "children": [{"name": t, "type": "leaf"} for t in abstract_leaves],
            },
            {
                "name": "Core Claim",
                "type": "branch",
                "color": MM_COLORS["Core Claim"],
                "children": [
                    {"name": t, "type": "leaf"}
                    for t in (summary.get("core_claim") or _leaves(["research_problem_candidates"]))[:3]
                ] or [{"name": "Not detected", "type": "leaf"}],
            },
            {
                "name": "Methods",
                "type": "branch",
                "color": MM_COLORS["Methods"],
                "children": [
                    {"name": t, "type": "leaf"}
                    for t in _leaves(["methodology_flow", "method_candidates"], 5)
                ] or [{"name": "Not detected", "type": "leaf"}],
            },
            {
                "name": "Findings",
                "type": "branch",
                "color": MM_COLORS["Findings"],
                "children": [
                    {"name": t, "type": "leaf"}
                    for t in _leaves(["result_candidates"], 4)
                ] or [{"name": "Not detected", "type": "leaf"}],
            },
            {
                "name": "Contributions",
                "type": "branch",
                "color": MM_COLORS["Contributions"],
                "children": [
                    {"name": t, "type": "leaf"}
                    for t in (summary.get("contributions") or [])[:4]
                ] or [{"name": "Not detected", "type": "leaf"}],
            },
            {
                "name": "Limitations",
                "type": "branch",
                "color": MM_COLORS["Limitations"],
                "children": [
                    {"name": t, "type": "leaf"}
                    for t in (summary.get("limitations") or [])[:3]
                ] or [{"name": "Not detected", "type": "leaf"}],
            },
            {
                "name": "Keywords",
                "type": "branch",
                "color": MM_COLORS["Keywords"],
                "children": [
                    {"name": kw, "type": "leaf"}
                    for kw in (analysis.get("keywords") or [])[:10]
                ] or [{"name": "None found", "type": "leaf"}],
            },
        ],
    }

    tree_json = json.dumps(tree, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Mind Map</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0f1117;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    overflow: hidden;
  }}
  #mm-canvas {{
    width: 100vw;
    height: 100vh;
  }}
  .node circle {{
    stroke-width: 2;
    transition: r 0.2s ease, stroke-width 0.2s ease;
    cursor: pointer;
  }}
  .node circle:hover {{
    stroke-width: 3.5;
  }}
  .node text {{
    pointer-events: none;
    user-select: none;
    dominant-baseline: central;
  }}
  .link {{
    fill: none;
    stroke-opacity: 0.55;
    transition: stroke-opacity 0.2s;
  }}
  .link:hover {{ stroke-opacity: 1; }}
  #tooltip {{
    position: fixed;
    background: rgba(15,17,23,0.92);
    color: #e8eaf0;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    max-width: 320px;
    line-height: 1.55;
    pointer-events: none;
    display: none;
    z-index: 999;
    backdrop-filter: blur(6px);
  }}
  #legend {{
    position: fixed;
    bottom: 14px;
    left: 14px;
    background: rgba(15,17,23,0.82);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 11px;
    color: #aab0be;
    line-height: 1.9;
  }}
  #legend .dot {{
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
  }}
  #hint {{
    position: fixed;
    top: 12px;
    right: 14px;
    color: rgba(170,176,190,0.6);
    font-size: 11px;
    text-align: right;
  }}
</style>
</head>
<body>
<svg id="mm-canvas"></svg>
<div id="tooltip"></div>
<div id="legend">
  <div><span class="dot" style="background:#5B8FF9"></span>Abstract</div>
  <div><span class="dot" style="background:#F6BD16"></span>Core Claim</div>
  <div><span class="dot" style="background:#7566A8"></span>Methods</div>
  <div><span class="dot" style="background:#28745F"></span>Findings</div>
  <div><span class="dot" style="background:#E8684A"></span>Contributions</div>
  <div><span class="dot" style="background:#9270CA"></span>Limitations</div>
  <div><span class="dot" style="background:#397CA5"></span>Keywords</div>
</div>
<div id="hint">Scroll to zoom · Drag to pan<br>Click branch to expand/collapse</div>

<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
const RAW_DATA = {tree_json};

const W = window.innerWidth;
const H = window.innerHeight;
const svg = d3.select("#mm-canvas")
  .attr("width", W)
  .attr("height", H);

const g = svg.append("g")
  .attr("transform", `translate(${{W/2}},${{H/2}})`);

svg.call(
  d3.zoom()
    .scaleExtent([0.25, 4])
    .on("zoom", e => g.attr("transform", e.transform.translate(W/2, H/2)))
);

const tooltip = d3.select("#tooltip");

// Radial layout
const radius = Math.min(W, H) * 0.42;

function buildTree(data) {{
  const root = d3.hierarchy(data);
  const layout = d3.tree()
    .size([2 * Math.PI, radius])
    .separation((a, b) => (a.parent === b.parent ? 1.2 : 2.4) / a.depth);
  return layout(root);
}}

function radialPoint(x, y) {{
  return [(y = +y) * Math.cos(x -= Math.PI / 2), y * Math.sin(x)];
}}

function branchColor(node) {{
  if (node.data.type === "root") return "#e8eaf0";
  if (node.data.type === "branch") return node.data.color;
  // Leaf inherits parent's color
  let n = node;
  while (n.parent) {{
    n = n.parent;
    if (n.data.type === "branch") return n.data.color;
  }}
  return "#aab0be";
}}

function draw() {{
  g.selectAll("*").remove();

  const root = buildTree(RAW_DATA);

  // Links
  g.append("g")
    .attr("class", "links")
    .selectAll("path")
    .data(root.links())
    .join("path")
    .attr("class", "link")
    .attr("d", d3.linkRadial().angle(d => d.x).radius(d => d.y))
    .attr("stroke", d => branchColor(d.target))
    .attr("stroke-width", d => d.target.data.type === "branch" ? 2.2 : 1.2);

  // Nodes
  const node = g.append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("transform", d => `translate(${{radialPoint(d.x, d.y)}})`)
    .on("mouseover", (event, d) => {{
      tooltip
        .style("display", "block")
        .html(`<strong>${{d.data.name}}</strong>`);
    }})
    .on("mousemove", event => {{
      tooltip
        .style("left", (event.clientX + 12) + "px")
        .style("top",  (event.clientY - 28) + "px");
    }})
    .on("mouseout", () => tooltip.style("display", "none"));

  // Circles
  node.append("circle")
    .attr("r", d => {{
      if (d.data.type === "root")   return 22;
      if (d.data.type === "branch") return 11;
      return 5;
    }})
    .attr("fill", d => {{
      if (d.data.type === "root") return "#263746";
      if (d.data.type === "branch") return branchColor(d);
      return branchColor(d) + "33";
    }})
    .attr("stroke", d => branchColor(d))
    .attr("stroke-width", d => d.data.type === "leaf" ? 1 : 2);

  // Labels
  node.append("text")
    .attr("dy", d => d.data.type === "leaf" ? "0.3em" : "0.35em")
    .attr("x", d => {{
      if (d.data.type === "root") return 0;
      const [px] = radialPoint(d.x, d.y);
      return px > 0 ? 14 : -14;
    }})
    .attr("text-anchor", d => {{
      if (d.data.type === "root") return "middle";
      const [px] = radialPoint(d.x, d.y);
      return px > 0 ? "start" : "end";
    }})
    .attr("font-size", d => {{
      if (d.data.type === "root")   return 13;
      if (d.data.type === "branch") return 11;
      return 9;
    }})
    .attr("font-weight", d => d.data.type !== "leaf" ? 700 : 400)
    .attr("fill", d => d.data.type === "root" ? "#e8eaf0" : branchColor(d))
    .text(d => {{
      const name = d.data.name;
      const maxLen = d.data.type === "root" ? 30 : d.data.type === "branch" ? 18 : 40;
      return name.length > maxLen ? name.slice(0, maxLen - 1) + "…" : name;
    }});
}}

draw();
window.addEventListener("resize", () => {{
  svg.attr("width", window.innerWidth).attr("height", window.innerHeight);
  draw();
}});
</script>
</body>
</html>"""

    return html
