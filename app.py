"""
app.py — PaperGraph · Research Intelligence Workspace
------------------------------------------------------
Tabs:
  1. Overview         — abstract, section map, reading stats, summary cards
  2. Evidence         — keywords, problems/methods/results candidates, flashcards
  3. Mind Map         — D3.js radial mind map
  4. Knowledge Graph  — pyvis interactive network
  5. Method Flow      — step-by-step methodology flowchart
  6. Document         — full extracted text explorer
  7. Export           — JSON, Markdown, Mind Map HTML downloads
"""

import json
import tempfile
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pdf_ingestion import extract_pdf
from paper_analysis import analyze_paper
from knowledge_graph import build_knowledge_graph, save_interactive_graph, build_mind_map_html

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PaperGraph — Research Intelligence",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Global CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@600;800&display=swap');

/* ── Design tokens ── */
:root {
  --bg:          #F7F8FA;
  --surface:     #FFFFFF;
  --text:        #1a2533;
  --muted:       #637381;
  --accent:      #356F70;
  --accent-h:    #28595A;
  --border:      #E1E6EB;
  --soft:        #EEF4F4;
  --radius:      10px;
  --shadow:      0 2px 12px rgba(0,0,0,.06);

  /* Category colours */
  --c-problem:   #B77B27;
  --c-method:    #7566A8;
  --c-finding:   #28745F;
  --c-keyword:   #397CA5;
  --c-contrib:   #E8684A;
  --c-limit:     #9270CA;
  --c-claim:     #F6BD16;
}

/* ── Base ── */
.stApp { background: var(--bg); color: var(--text); font-family: 'Inter', 'Segoe UI', sans-serif; }
[data-testid="stHeader"]   { background: rgba(247,248,250,.96); }
[data-testid="stMain"]     { background: var(--bg); }
.block-container           { max-width: 1440px; padding-top: 1.6rem; padding-bottom: 3rem; }

/* ── Typography ── */
h1,h2,h3,h4 { color: var(--text) !important; letter-spacing: -.025em; font-weight: 700 !important; }
h1 { font-size: 2rem !important; line-height: 1.25 !important; }
h2 { font-size: 1.4rem !important; }
h3 { font-size: 1.08rem !important; }
p, li, label, .stMarkdown { color: var(--text); line-height: 1.65; }
small, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size: .92rem; }
[data-testid="stSidebar"] hr { border-color: var(--border); }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap: 1.1rem;
  border-bottom: 1px solid var(--border);
  background: transparent;
}
.stTabs [data-baseweb="tab"] {
  height: 46px; padding: 0 .2rem;
  background: transparent; color: var(--muted);
  border-radius: 0; font-size: .91rem; font-weight: 500;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--accent); }
.stTabs [aria-selected="true"]     { color: var(--accent) !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"]    { background-color: transparent; }

/* ── Buttons ── */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
  background: var(--accent); color: #fff;
  border: 1px solid var(--accent); border-radius: 6px;
  padding: .48rem .9rem; font-weight: 600;
  transition: background 120ms ease, border-color 120ms ease;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: var(--accent-h); border-color: var(--accent-h); color: #fff;
}
.stButton > button:focus,
.stDownloadButton > button:focus { box-shadow: 0 0 0 2px #B7D5D3; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea,
.stSelectbox [data-baseweb="select"], .stNumberInput input {
  background: #fff; color: var(--text);
  border-color: #CDD6DE; border-radius: 6px;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
  border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent);
}

/* ── Containers / metrics ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface); border-color: var(--border) !important;
  border-radius: var(--radius); box-shadow: none;
}
[data-testid="stMetric"] {
  background: #fff; border: 1px solid var(--border);
  border-radius: var(--radius); padding: .9rem 1rem;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: .82rem; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-size: 1.55rem; font-weight: 700; }

/* ── Alerts / expanders ── */
[data-testid="stAlert"] { border-radius: 6px; border-width: 1px; box-shadow: none; }
[data-testid="stExpander"] {
  background: #fff; border: 1px solid var(--border); border-radius: 6px;
}
[data-testid="stExpander"] summary { color: var(--text); font-weight: 550; }

/* ── Tables ── */
[data-testid="stDataFrame"],
[data-testid="stTable"] { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }

/* ── Misc ── */
hr { border-color: var(--border); }
a  { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { color: var(--accent-h); }
iframe { border: 1px solid var(--border); border-radius: 6px; background: #fff; }
button:focus-visible, a:focus-visible, input:focus-visible {
  outline: 2px solid var(--accent); outline-offset: 2px;
}

/* ── Custom components ── */

/* Brand */
.brand {
  font-family: 'Manrope', 'Inter', sans-serif;
  font-size: 1.55rem; font-weight: 800;
  color: var(--text); letter-spacing: -.04em;
}
.brand span { color: var(--accent); }
.sidebar-caption {
  font-size: .68rem; font-weight: 600; letter-spacing: .1em;
  color: var(--muted); margin-top: .15rem; margin-bottom: 1rem;
}

/* Hero */
.hero { padding: 1.5rem 0 1.2rem; }
.eyebrow {
  font-size: .68rem; font-weight: 700; letter-spacing: .12em;
  color: var(--accent); text-transform: uppercase; margin-bottom: .5rem;
}
.hero-title {
  font-family: 'Manrope', 'Inter', sans-serif;
  font-size: 2.1rem; font-weight: 800;
  color: var(--text); line-height: 1.2; margin-bottom: .7rem;
}
.hero-sub { font-size: .97rem; color: var(--muted); max-width: 680px; line-height: 1.6; }

/* Cards */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1.1rem 1.3rem;
  margin-bottom: .75rem; box-shadow: var(--shadow);
}
.card-title { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: .35rem; }
.card-text  { font-size: .88rem; color: var(--muted); line-height: 1.55; }

/* Summary cards */
.sum-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1rem 1.2rem 1.1rem;
  box-shadow: var(--shadow); height: 100%;
}
.sum-card .sc-label {
  font-size: .65rem; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; margin-bottom: .45rem;
  padding: .18rem .5rem; border-radius: 4px; display: inline-block;
}
.sum-card .sc-body { font-size: .875rem; color: var(--text); line-height: 1.6; }
.sum-card .sc-item { margin-bottom: .4rem; padding-left: .85rem; position: relative; }
.sum-card .sc-item::before {
  content: "›"; position: absolute; left: 0;
  color: var(--muted); font-weight: 700;
}

/* Reading stats bar */
.stats-bar {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: .85rem 1.3rem;
  display: flex; flex-wrap: wrap; gap: 1.5rem; align-items: center;
  margin-bottom: 1rem; box-shadow: var(--shadow);
}
.stat-item { display: flex; flex-direction: column; align-items: flex-start; }
.stat-val  { font-size: 1.2rem; font-weight: 700; color: var(--text); line-height: 1; }
.stat-lbl  { font-size: .7rem; font-weight: 600; letter-spacing: .06em;
             color: var(--muted); margin-top: .2rem; text-transform: uppercase; }
.difficulty-chip {
  border-radius: 20px; padding: .22rem .7rem;
  font-size: .75rem; font-weight: 700; letter-spacing: .04em;
}

/* Keyword pills */
.pill {
  display: inline-block; background: var(--soft);
  color: var(--accent); border: 1px solid #B7D5D3;
  border-radius: 20px; padding: .22rem .7rem;
  margin: .2rem; font-size: .82rem; font-weight: 500;
}

/* Flashcards */
.flashcard {
  background: linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%);
  border: 1px solid #dde3f0; border-radius: var(--radius);
  padding: 1rem 1.2rem; margin-bottom: .6rem;
  transition: box-shadow .15s ease;
}
.flashcard:hover { box-shadow: 0 4px 16px rgba(53,111,112,.12); }
.flashcard .fc-term {
  font-size: .78rem; font-weight: 700; letter-spacing: .08em;
  color: var(--accent); text-transform: uppercase; margin-bottom: .35rem;
}
.flashcard .fc-q {
  font-size: .9rem; font-weight: 600; color: var(--text); margin-bottom: .5rem;
}
.flashcard .fc-a {
  font-size: .85rem; color: #4a5568; line-height: 1.6;
  border-left: 3px solid var(--accent); padding-left: .7rem;
}

/* Method flow */
.flow-step {
  display: flex; align-items: flex-start; gap: .85rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: .85rem 1.1rem;
  margin-bottom: .55rem; box-shadow: var(--shadow);
  transition: transform .12s ease, box-shadow .12s ease;
}
.flow-step:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 16px rgba(53,111,112,.12);
}
.flow-num {
  min-width: 32px; height: 32px; border-radius: 50%;
  background: var(--accent); color: #fff;
  font-weight: 700; font-size: .9rem;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.flow-text { font-size: .875rem; color: var(--text); line-height: 1.55; padding-top: .15rem; }
.flow-arrow { text-align: center; color: var(--muted); font-size: 1.3rem; margin: .1rem 0; }

/* Section / footer */
.section-title {
  font-family: 'Manrope', sans-serif;
  font-size: 1.35rem; font-weight: 800;
  color: var(--text); margin-bottom: .2rem; margin-top: .5rem;
}
.section-sub { font-size: .88rem; color: var(--muted); margin-bottom: 1.1rem; }
.footer {
  text-align: center; font-size: .72rem; letter-spacing: .12em;
  color: #B0BAC4; margin-top: 2.5rem; padding-top: .75rem;
  border-top: 1px solid var(--border);
}

/* Metric card custom */
.metric {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); padding: .85rem 1rem;
  box-shadow: var(--shadow);
}
.metric-label {
  font-size: .7rem; font-weight: 700; letter-spacing: .07em;
  color: var(--muted); text-transform: uppercase; margin-bottom: .3rem;
}
.metric-value { font-size: 1.55rem; font-weight: 700; color: var(--text); }

/* Responsive */
@media (max-width: 768px) {
  .block-container { padding: 1rem 1rem 2rem; }
  h1 { font-size: 1.65rem !important; }
  .stTabs [data-baseweb="tab-list"] { gap: .6rem; }
  [data-testid="stMetric"] { padding: .7rem; }
  .hero-title { font-size: 1.6rem; }
  .stats-bar { gap: 1rem; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

for key, default in {
    "paper_result": None,
    "paper_analysis": None,
    "paper_graph_html": None,
    "paper_mind_map_html": None,
    "paper_graph_stats": None,
    "paper_graph_error": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="brand">Paper<span>Graph</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-caption">RESEARCH INTELLIGENCE WORKSPACE</div>', unsafe_allow_html=True)

    st.markdown("### Research desk")
    st.caption("Upload a text-based paper to begin.")
    uploaded_file = st.file_uploader(
        "Research paper (PDF)", type=["pdf"], help="Maximum size: 25 MB"
    )
    if uploaded_file:
        st.caption(f"Selected: {uploaded_file.name} · {uploaded_file.size / 1024 / 1024:.1f} MB")

    process_clicked = st.button(
        "✦  Analyze paper", type="primary",
        disabled=uploaded_file is None, use_container_width=True,
    )

    st.divider()

    # Quick stats after analysis
    rs = (st.session_state.paper_analysis or {}).get("reading_stats", {})
    if rs:
        st.markdown("**QUICK STATS**")
        diff = rs.get("difficulty_label", "—")
        chip_color = {"Accessible": "#28745F", "Academic": "#B77B27", "Highly Technical": "#9270CA"}.get(diff, "#637381")
        st.markdown(
            f'<span class="difficulty-chip" style="background:{chip_color}22;color:{chip_color};border:1px solid {chip_color}44">{diff}</span>',
            unsafe_allow_html=True,
        )
        st.caption(f"⏱ ~{rs.get('reading_minutes', '?')} min read · {rs.get('word_count', 0):,} words")
        st.caption(f"📖 {rs.get('page_count', 0)} pages · ~{rs.get('citation_count', 0)} citations")
        st.divider()

    st.markdown("**WORKSPACE**")
    st.caption("01  Overview & summary")
    st.caption("02  Evidence & flashcards")
    st.caption("03  Mind map")
    st.caption("04  Knowledge graph")
    st.caption("05  Method flow")
    st.caption("06  Document explorer")
    st.caption("07  Export")
    st.divider()

    st.markdown("**PROCESSING NOTES**")
    st.caption("PDF extraction · Local NLP · Interactive visualizations")
    st.caption("No external AI API key required.")

    if st.button("Clear current analysis", use_container_width=True):
        for key in (
            "paper_result", "paper_analysis", "paper_graph_html",
            "paper_mind_map_html", "paper_graph_stats", "paper_graph_error",
        ):
            st.session_state[key] = None
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# Processing pipeline
# ─────────────────────────────────────────────────────────────────────────────

if process_clicked and uploaded_file is not None:
    if uploaded_file.size > 25 * 1024 * 1024:
        st.error("This PDF exceeds the 25 MB upload limit.")
    else:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
                temp.write(uploaded_file.getvalue())
                temp_path = Path(temp.name)

            progress = st.progress(0, text="Preparing document…")

            with st.spinner("Extracting PDF text and page structure…"):
                result = extract_pdf(temp_path)
            progress.progress(25, text="Extracted document text")

            if result.get("is_likely_scanned"):
                st.warning(
                    "Very little text was extracted. This may be a scanned PDF; OCR is not included yet."
                )

            with st.spinner("Running NLP analysis (keywords, summaries, flashcards)…"):
                # Merge title into the dict so analyze_paper has access to it
                result["title"] = result.get("title", "Research Paper")
                analysis = analyze_paper(result)
                # Also make abstract available to mind-map builder
                analysis["abstract"] = result.get("abstract", "")
                analysis["title"]    = result.get("title", "Research Paper")
            progress.progress(65, text="Analyzing paper content")

            graph_error = None
            graph_html  = None
            mind_map_html = None
            graph_stats = {"nodes": 0, "edges": 0}

            try:
                with st.spinner("Building knowledge graph…"):
                    # Pass merged analysis dict (includes title + all NLP fields)
                    merged = {**result, **analysis}
                    graph = build_knowledge_graph(merged)
                    graph_stats = {
                        "nodes": graph.number_of_nodes(),
                        "edges": graph.number_of_edges(),
                    }
                    graph_html = save_interactive_graph(graph)
            except Exception as exc:
                graph_error = f"{type(exc).__name__}: {exc}"

            progress.progress(82, text="Generating mind map…")

            try:
                with st.spinner("Generating mind map…"):
                    mind_map_html = build_mind_map_html(
                        result.get("title", "Research Paper"), analysis
                    )
            except Exception:
                mind_map_html = None

            progress.progress(100, text="Analysis complete ✦")

            st.session_state.paper_result       = result
            st.session_state.paper_analysis     = analysis
            st.session_state.paper_graph_html   = graph_html
            st.session_state.paper_mind_map_html = mind_map_html
            st.session_state.paper_graph_stats  = graph_stats
            st.session_state.paper_graph_error  = graph_error

            st.success("Paper analysis completed. Explore the tabs below.")

        except Exception as exc:
            st.error(f"Could not process this PDF: {type(exc).__name__}: {exc}")
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

# ─────────────────────────────────────────────────────────────────────────────
# Hero header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
  <div class="eyebrow">AI-ASSISTED RESEARCH DESK</div>
  <div class="hero-title">Read the paper.<br>Map the ideas.</div>
  <div class="hero-sub">A workspace for exploring research papers through structured summaries, semantic insights, interactive mind maps, and concept flashcards. Treat model outputs as research leads—not verified conclusions.</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Landing state (no paper loaded)
# ─────────────────────────────────────────────────────────────────────────────

result   = st.session_state.paper_result
analysis = st.session_state.paper_analysis
graph_html = st.session_state.paper_graph_html
mind_map_html = st.session_state.paper_mind_map_html

if result is None or analysis is None:
    a, b, c, d = st.columns(4)
    for col, icon, title, body in [
        (a, "🗺️", "Mind Map",     "Visual radial map of the paper's entire conceptual structure."),
        (b, "📋", "Summary Cards", "TL;DR breakdown: core claim, methods, contributions, limitations."),
        (c, "🃏", "Flashcards",    "Auto Q&A cards per keyword to accelerate comprehension."),
        (d, "🔀", "Method Flow",   "Step-by-step visual pipeline of the paper's methodology."),
    ]:
        with col:
            st.markdown(
                f'<div class="card"><div style="font-size:26px">{icon}</div>'
                f'<div class="card-title">{title}</div>'
                f'<div class="card-text">{body}</div></div>',
                unsafe_allow_html=True,
            )
    st.info("Upload a research PDF from the sidebar and select **Analyze paper** to populate your workspace.")
    st.markdown('<div class="footer">PAPERGRAPH · RESEARCH DISCOVERY WORKSPACE</div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Paper title banner + top metrics
# ─────────────────────────────────────────────────────────────────────────────

title_str    = escape(str(result.get("title") or "Untitled research paper"))
filename_str = escape(str(result.get("filename") or "Uploaded PDF"))
st.markdown(
    f'<div class="card"><div class="eyebrow">ACTIVE PAPER</div>'
    f'<div style="font-family:Manrope,sans-serif;font-size:21px;font-weight:800;color:#172033">{title_str}</div>'
    f'<div class="card-text">{filename_str}</div></div>',
    unsafe_allow_html=True,
)

stats   = st.session_state.paper_graph_stats or {}
rs_data = analysis.get("reading_stats", {})

metrics = [
    ("PAGES",               result.get("page_count", 0)),
    ("WORDS",               f'{rs_data.get("word_count", 0):,}'),
    ("~READING TIME",       f'{rs_data.get("reading_minutes", "?")} min'),
    ("KEYWORDS",            len(analysis.get("keywords", []))),
    ("FLASHCARDS",          len(analysis.get("flashcards", []))),
    ("GRAPH NODES / EDGES", f'{stats.get("nodes", 0)} / {stats.get("edges", 0)}'),
]
cols = st.columns(len(metrics))
for col, (label, value) in zip(cols, metrics):
    with col:
        st.markdown(
            f'<div class="metric"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

(
    overview_tab, insights_tab, mindmap_tab, graph_tab,
    flow_tab, document_tab, export_tab,
) = st.tabs([
    "📄 Overview",
    "✳ Evidence & Flashcards",
    "🗺️ Mind Map",
    "🕸️ Knowledge Graph",
    "🔀 Method Flow",
    "☰ Document",
    "↗ Export",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ══════════════════════════════════════════════════════════════════════════════

with overview_tab:
    st.markdown(
        '<div class="section-title">Paper overview</div>'
        '<div class="section-sub">Start with the document\'s own framing, then review AI-generated summaries.</div>',
        unsafe_allow_html=True,
    )

    # Reading stats bar
    if rs_data:
        diff       = rs_data.get("difficulty_label", "Unknown")
        chip_color = {"Accessible": "#28745F", "Academic": "#B77B27", "Highly Technical": "#9270CA"}.get(diff, "#637381")
        flesch_txt = f'{rs_data["flesch_score"]} Flesch' if rs_data.get("flesch_score") is not None else "—"
        grade_txt  = f'Grade {rs_data["grade_level"]}' if rs_data.get("grade_level") is not None else "—"

        st.markdown(f"""
        <div class="stats-bar">
          <div class="stat-item">
            <span class="stat-val">
              <span class="difficulty-chip" style="background:{chip_color}22;color:{chip_color};border:1px solid {chip_color}44">
                {diff}
              </span>
            </span>
            <span class="stat-lbl">Difficulty</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">{rs_data.get('reading_minutes','?')} min</span>
            <span class="stat-lbl">Est. Read Time</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">{rs_data.get('word_count',0):,}</span>
            <span class="stat-lbl">Words</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">{rs_data.get('jargon_pct',0)}%</span>
            <span class="stat-lbl">Jargon Density</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">~{rs_data.get('citation_count',0)}</span>
            <span class="stat-lbl">Citations</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">{flesch_txt}</span>
            <span class="stat-lbl">Readability</span>
          </div>
          <div class="stat-item">
            <span class="stat-val">{grade_txt}</span>
            <span class="stat-lbl">Reading Level</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Abstract
    st.markdown("#### Abstract")
    if result.get("abstract"):
        st.write(result["abstract"])
    else:
        st.info("No abstract was detected. Check the extracted document for formatting or heading issues.")

    st.markdown("---")

    # Summary cards
    sc = analysis.get("summary_cards", {})
    if any(sc.values()):
        st.markdown("#### AI-generated summary cards")
        st.caption("Automated candidates extracted via semantic search. Verify all claims against the source paper.")

        def _render_sum_card(label_text, color, items, col):
            items_html = "".join(
                f'<div class="sc-item">{escape(str(item))}</div>'
                for item in (items or ["Not detected"])
            )
            col.markdown(
                f'<div class="sum-card">'
                f'<span class="sc-label" style="background:{color}22;color:{color};border:1px solid {color}44">'
                f'{label_text}</span>'
                f'<div class="sc-body">{items_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        c1, c2 = st.columns(2)
        _render_sum_card("🎯 Core Claim",    "#F6BD16", sc.get("core_claim"),     c1)
        _render_sum_card("✨ Contributions", "#E8684A", sc.get("contributions"),  c2)

        c3, c4 = st.columns(2)
        _render_sum_card("⚠️ Limitations",  "#9270CA", sc.get("limitations"),    c3)
        _render_sum_card("🔭 Future Work",  "#5B8FF9", sc.get("future_work"),    c4)

    st.markdown("---")

    # Section map + extraction quality
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Section map")
        sections = result.get("sections", [])
        if sections:
            st.dataframe(sections, use_container_width=True, hide_index=True)
        else:
            st.info("No recognized section headings were detected.")
    with right:
        st.markdown("#### Extraction quality")
        total = result.get("total_characters", 0)
        pages = max(1, result.get("page_count", 0))
        st.metric("Average characters per page", f"{total / pages:,.0f}")
        if result.get("is_likely_scanned"):
            st.warning("This document may be scanned. OCR is not currently included.")
        else:
            st.caption("Text extraction returned content. Still verify equations, tables, and multi-column reading order.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Evidence & Flashcards
# ══════════════════════════════════════════════════════════════════════════════

with insights_tab:
    st.markdown(
        '<div class="section-title">Evidence & NLP Insights</div>'
        '<div class="section-sub">Automated candidates — validate against the source paper before citing.</div>',
        unsafe_allow_html=True,
    )

    # Keywords
    keywords = analysis.get("keywords", [])
    st.markdown("#### Candidate keywords")
    if keywords:
        st.markdown(
            "".join(f'<span class="pill">{escape(str(w))}</span>' for w in keywords),
            unsafe_allow_html=True,
        )
    else:
        st.info("No keywords found. The abstract or extracted text may be too short.")

    st.markdown("---")

    # Evidence groups
    groups = [
        ("Research problem / gap candidates", "research_problem_candidates", "What problem or gap might the paper address?"),
        ("Method candidates",                 "method_candidates",           "Which methods or approaches appear relevant?"),
        ("Result candidates",                 "result_candidates",           "Which sentences may describe findings?"),
    ]
    for heading, key, description in groups:
        st.markdown(f"#### {heading}")
        st.caption(description)
        candidates = analysis.get(key, [])
        if not candidates:
            st.info("No candidates were found for this category.")
        else:
            for i, sentence in enumerate(candidates, 1):
                with st.container(border=True):
                    st.caption(f"CANDIDATE {i} · VERIFY IN SOURCE")
                    st.write(sentence)

    st.warning("PaperGraph ranks sentences by semantic similarity; it does not prove that a sentence is a true research gap, method, or result.")

    st.markdown("---")

    # Flashcards
    flashcards = analysis.get("flashcards", [])
    st.markdown("#### 🃏 Concept flashcards")
    st.caption("Auto-generated Q&A cards — one per keyword. Use them to test your understanding of key concepts.")

    if not flashcards:
        st.info("No flashcards generated. The paper may be too short or have very few extractable keywords.")
    else:
        # 2-column layout
        fc_cols = st.columns(2)
        for i, fc in enumerate(flashcards):
            term = escape(str(fc.get("term", "")))
            expl = escape(str(fc.get("explanation", "")))
            fc_cols[i % 2].markdown(
                f'<div class="flashcard">'
                f'<div class="fc-term">{term}</div>'
                f'<div class="fc-q">What is <em>{term}</em> in this paper?</div>'
                f'<div class="fc-a">{expl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Mind Map
# ══════════════════════════════════════════════════════════════════════════════

with mindmap_tab:
    st.markdown(
        '<div class="section-title">Mind Map</div>'
        '<div class="section-sub">Radial concept map of the paper — zoom, pan, and hover over nodes for full text.</div>',
        unsafe_allow_html=True,
    )

    if mind_map_html:
        st.caption("7 branches: Abstract · Core Claim · Methods · Findings · Contributions · Limitations · Keywords")
        components.html(mind_map_html, height=700, scrolling=False)
        st.download_button(
            "Download mind map (HTML)",
            data=mind_map_html.encode("utf-8"),
            file_name="papergraph-mind-map.html",
            mime="text/html",
            use_container_width=True,
        )
        with st.expander("How to use the mind map"):
            st.write(
                "**Scroll** to zoom in/out. **Drag** the background to pan. "
                "**Hover** any node to see its full text in a tooltip. "
                "The central node is the paper title; each branch represents a conceptual category."
            )
    else:
        st.warning("Mind map could not be generated. Re-analyze the paper or check the console for errors.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Knowledge Graph
# ══════════════════════════════════════════════════════════════════════════════

with graph_tab:
    st.markdown(
        '<div class="section-title">Knowledge Graph</div>'
        '<div class="section-sub">Entity-relationship network — drag nodes, zoom, hover for details.</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.paper_graph_error:
        st.error("The graph could not be generated.")
        st.code(st.session_state.paper_graph_error)
    elif graph_html:
        st.caption(f'{stats.get("nodes", 0)} nodes · {stats.get("edges", 0)} relationships')
        components.html(graph_html, height=680, scrolling=True)
        st.download_button(
            "Download interactive graph (HTML)",
            data=graph_html.encode("utf-8"),
            file_name="papergraph-knowledge-graph.html",
            mime="text/html",
            use_container_width=True,
        )
        st.caption("Open the downloaded HTML in any modern browser. Graph is local to this paper only.")
    else:
        st.warning("No graph HTML available. Re-analyze the paper.")

    with st.expander("How to interpret this graph"):
        st.write(
            "Nodes represent the paper, candidate problem/method/finding sentences, and extracted keywords. "
            "Edges show 'extracted from' relationships — not proven causal or scientific links."
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Method Flow
# ══════════════════════════════════════════════════════════════════════════════

with flow_tab:
    st.markdown(
        '<div class="section-title">Methodology Flow</div>'
        '<div class="section-sub">Step-by-step pipeline extracted from the paper\'s methods section. Verify order and completeness against the source.</div>',
        unsafe_allow_html=True,
    )

    flow_steps = analysis.get("methodology_flow", [])

    if not flow_steps:
        st.info(
            "No methodology steps were detected. This can happen if the paper doesn't use numbered steps or "
            "sequential language ('first', 'then', 'finally', etc.) in its methods section."
        )
    else:
        st.caption(f"{len(flow_steps)} steps detected")
        steps_html = ""
        for i, step in enumerate(flow_steps):
            steps_html += (
                f'<div class="flow-step">'
                f'<div class="flow-num">{i + 1}</div>'
                f'<div class="flow-text">{escape(str(step))}</div>'
                f'</div>'
            )
            if i < len(flow_steps) - 1:
                steps_html += '<div class="flow-arrow">↓</div>'

        st.markdown(steps_html, unsafe_allow_html=True)

        st.caption("These steps are extracted via pattern matching and semantic ranking — not guaranteed to be in the correct order or to capture all steps.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Document Explorer
# ══════════════════════════════════════════════════════════════════════════════

with document_tab:
    st.markdown(
        '<div class="section-title">Document explorer</div>'
        '<div class="section-sub">Inspect extracted text page by page. Compare important passages with the original PDF.</div>',
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "Search extracted text",
        placeholder="Search for a term, method, dataset, metric…",
    )
    pages = result.get("pages", [])
    matching = [
        page for page in pages
        if not query or query.casefold() in page.get("text", "").casefold()
    ]

    st.caption(f"{len(matching)} of {len(pages)} pages shown")

    for page in matching:
        with st.expander(
            f'Page {page.get("page", "?")} · {page.get("characters", len(page.get("text", "")))} characters'
        ):
            if page.get("text"):
                st.text(page["text"])
            else:
                st.warning("No extractable text on this page.")

    if query and not matching:
        st.info("No matching pages. Try a shorter search term.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — Export
# ══════════════════════════════════════════════════════════════════════════════

with export_tab:
    st.markdown(
        '<div class="section-title">Export research notes</div>'
        '<div class="section-sub">Download structured outputs for your literature workflow.</div>',
        unsafe_allow_html=True,
    )

    # JSON bundle
    bundle = {
        "document": {
            k: result.get(k)
            for k in ("filename", "title", "abstract", "sections", "page_count", "total_characters", "is_likely_scanned")
        },
        "analysis": {
            k: analysis.get(k)
            for k in ("keywords", "research_problem_candidates", "method_candidates", "result_candidates",
                      "summary_cards", "methodology_flow", "reading_stats")
        },
        "graph": stats,
        "notice": "Automated outputs are candidates and require verification against the source paper.",
    }
    st.download_button(
        "📦 Download analysis bundle (JSON)",
        data=json.dumps(bundle, ensure_ascii=False, indent=2),
        file_name="papergraph-analysis.json",
        mime="application/json",
        use_container_width=True,
    )

    # Full extraction JSON
    extraction = json.dumps(result, ensure_ascii=False, indent=2)
    st.download_button(
        "📄 Download full extracted text (JSON)",
        data=extraction,
        file_name="papergraph-extraction.json",
        mime="application/json",
        use_container_width=True,
    )

    # Markdown research notes
    sc = analysis.get("summary_cards", {})
    md = [
        f"# {result.get('title', 'Research paper')}",
        "",
        f"**File:** {result.get('filename', '')}",
        "",
        "## Abstract",
        "",
        result.get("abstract") or "No abstract detected.",
        "",
        "## Summary",
        "",
        "### Core Claim",
        "",
    ]
    md += [f"- {x}" for x in (sc.get("core_claim") or ["Not detected"])]
    md += ["", "### Contributions", ""]
    md += [f"- {x}" for x in (sc.get("contributions") or ["Not detected"])]
    md += ["", "### Limitations", ""]
    md += [f"- {x}" for x in (sc.get("limitations") or ["Not detected"])]
    md += ["", "### Future Work", ""]
    md += [f"- {x}" for x in (sc.get("future_work") or ["Not detected"])]
    md += ["", "## Candidate Keywords", ""]
    md += [f"- {x}" for x in analysis.get("keywords", [])]
    for heading, key in [
        ("Research problem / gap candidates", "research_problem_candidates"),
        ("Method candidates",                 "method_candidates"),
        ("Result candidates",                 "result_candidates"),
    ]:
        md += ["", f"## {heading}", ""]
        md += [f"- {x}" for x in analysis.get(key, [])] or ["- No candidates found."]

    md += ["", "## Methodology Flow", ""]
    for i, step in enumerate(analysis.get("methodology_flow", []), 1):
        md.append(f"{i}. {step}")

    md += ["", "## Concept Flashcards", ""]
    for fc in analysis.get("flashcards", []):
        md += [f"**Q: What is {fc.get('term', '')}?**", f"> {fc.get('explanation', '')}", ""]

    md += ["", "> Note: These are automated candidates. Verify all claims against the original PDF."]

    st.download_button(
        "📝 Download research notes (Markdown)",
        data="\n".join(md),
        file_name="papergraph-research-notes.md",
        mime="text/markdown",
        use_container_width=True,
    )

    # Mind map HTML
    if mind_map_html:
        st.download_button(
            "🗺️ Download mind map (HTML)",
            data=mind_map_html.encode("utf-8"),
            file_name="papergraph-mind-map.html",
            mime="text/html",
            use_container_width=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="footer">PAPERGRAPH · READ CAREFULLY · VERIFY EVIDENCE · CONNECT IDEAS</div>',
    unsafe_allow_html=True,
)
