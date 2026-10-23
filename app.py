import json
import tempfile
from pathlib import Path
from html import escape

import streamlit as st
import streamlit.components.v1 as components

from pdf_ingestion import extract_pdf
from paper_analysis import analyze_paper
from knowledge_graph import build_knowledge_graph, save_interactive_graph

st.set_page_config(
    page_title="PaperGraph — Research Intelligence",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
/* --------------------------------------------------
   PaperGraph — Research-focused visual system
   -------------------------------------------------- */

:root {
    --pg-bg: #F7F8FA;
    --pg-surface: #FFFFFF;
    --pg-text: #263746;
    --pg-muted: #637381;
    --pg-accent: #356F70;
    --pg-accent-hover: #28595A;
    --pg-border: #E1E6EB;
    --pg-soft: #EEF4F4;
}

/* App background and typography */
.stApp {
    background: var(--pg-bg);
    color: var(--pg-text);
    font-family: "Inter", "Segoe UI", sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(247, 248, 250, 0.96);
}

[data-testid="stMain"] {
    background: var(--pg-bg);
}

.block-container {
    max-width: 1440px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Headings: clear hierarchy, no oversized display text */
h1, h2, h3, h4 {
    color: var(--pg-text) !important;
    letter-spacing: -0.025em;
    font-weight: 650 !important;
}

h1 {
    font-size: 2rem !important;
    line-height: 1.25 !important;
}

h2 {
    font-size: 1.4rem !important;
}

h3 {
    font-size: 1.08rem !important;
}

p, li, label, .stMarkdown {
    color: var(--pg-text);
    line-height: 1.65;
}

small, [data-testid="stCaptionContainer"] {
    color: var(--pg-muted) !important;
}

/* Sidebar: quiet navigation, not a dark decorative panel */
[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--pg-border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.92rem;
}

[data-testid="stSidebar"] hr {
    border-color: var(--pg-border);
}

/* Tabs: restrained academic workspace */
.stTabs [data-baseweb="tab-list"] {
    gap: 1.25rem;
    border-bottom: 1px solid var(--pg-border);
    background: transparent;
}

.stTabs [data-baseweb="tab"] {
    height: 46px;
    padding: 0 0.25rem;
    background: transparent;
    color: var(--pg-muted);
    border-radius: 0;
    font-size: 0.93rem;
    font-weight: 500;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--pg-accent);
}

.stTabs [aria-selected="true"] {
    color: var(--pg-accent) !important;
    font-weight: 650 !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: var(--pg-accent);
    height: 2px;
}

.stTabs [data-baseweb="tab-border"] {
    background-color: transparent;
}

/* Buttons: one purposeful accent color */
.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] button {
    background: var(--pg-accent);
    color: #FFFFFF;
    border: 1px solid var(--pg-accent);
    border-radius: 6px;
    padding: 0.48rem 0.9rem;
    font-weight: 600;
    transition: background 120ms ease, border-color 120ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] button:hover {
    background: var(--pg-accent-hover);
    border-color: var(--pg-accent-hover);
    color: #FFFFFF;
}

.stButton > button:focus,
.stDownloadButton > button:focus {
    box-shadow: 0 0 0 2px #B7D5D3;
}

/* Inputs: clear borders and visible focus */
.stTextInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"],
.stNumberInput input {
    background: #FFFFFF;
    color: var(--pg-text);
    border-color: #CDD6DE;
    border-radius: 6px;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: var(--pg-accent);
    box-shadow: 0 0 0 1px var(--pg-accent);
}

/* Content containers: subtle boundaries, no heavy shadows */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--pg-surface);
    border-color: var(--pg-border) !important;
    border-radius: 8px;
    box-shadow: none;
}

/* Metrics: compact, information-first */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--pg-border);
    border-radius: 8px;
    padding: 0.9rem 1rem;
}

[data-testid="stMetricLabel"] {
    color: var(--pg-muted) !important;
    font-size: 0.82rem;
}

[data-testid="stMetricValue"] {
    color: var(--pg-text) !important;
    font-size: 1.55rem;
    font-weight: 650;
}

/* Alerts and status messages */
[data-testid="stAlert"] {
    border-radius: 6px;
    border-width: 1px;
    box-shadow: none;
}

/* Expanders: useful for source text and evidence details */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid var(--pg-border);
    border-radius: 6px;
}

[data-testid="stExpander"] summary {
    color: var(--pg-text);
    font-weight: 550;
}

/* Tables: readable paper metadata and evidence */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid var(--pg-border);
    border-radius: 6px;
    overflow: hidden;
}

/* Horizontal dividers */
hr {
    border-color: var(--pg-border);
}

/* Links */
a {
    color: var(--pg-accent);
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
}

a:hover {
    color: var(--pg-accent-hover);
}

/* Interactive graph frame */
iframe {
    border: 1px solid var(--pg-border);
    border-radius: 6px;
    background: #FFFFFF;
}

/* Keyboard accessibility */
button:focus-visible,
a:focus-visible,
input:focus-visible {
    outline: 2px solid var(--pg-accent);
    outline-offset: 2px;
}

/* Smaller screens */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 1rem 2rem;
    }

    h1 {
        font-size: 1.65rem !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.6rem;
    }

    [data-testid="stMetric"] {
        padding: 0.7rem;
    }
}
</style>
""", unsafe_allow_html=True)

for key, default in {
    "paper_result": None, "paper_analysis": None, "paper_graph_html": None,
    "paper_graph_stats": None, "paper_graph_error": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.markdown('<div class="brand">Paper<span>Graph</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-caption">RESEARCH INTELLIGENCE WORKSPACE</div>', unsafe_allow_html=True)
    st.markdown("### Research desk")
    st.caption("Upload a text-based paper to begin.")
    uploaded_file = st.file_uploader("Research paper (PDF)", type=["pdf"], help="Maximum size: 25 MB")
    if uploaded_file:
        st.caption(f"Selected: {uploaded_file.name} · {uploaded_file.size / 1024 / 1024:.1f} MB")
    process_clicked = st.button("✦  Analyze paper", type="primary", disabled=uploaded_file is None, use_container_width=True)
    st.divider()
    st.markdown("**WORKSPACE**")
    st.caption("01  Paper overview")
    st.caption("02  Evidence & insights")
    st.caption("03  Knowledge graph")
    st.caption("04  Document explorer")
    st.caption("05  Export")
    st.divider()
    st.markdown("**PROCESSING NOTES**")
    st.caption("PDF extraction · Local NLP · Interactive graph")
    st.caption("No external AI API key required.")
    if st.button("Clear current analysis", use_container_width=True):
        for key in ("paper_result", "paper_analysis", "paper_graph_html", "paper_graph_stats", "paper_graph_error"):
            st.session_state[key] = None
        st.rerun()

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
            progress.progress(35, text="Extracted document text")
            if result.get("is_likely_scanned"):
                st.warning("Very little text was extracted. This may be a scanned PDF; OCR is not included yet.")
            with st.spinner("Finding keywords and candidate evidence…"):
                analysis = analyze_paper(result)
            progress.progress(70, text="Analyzing paper content")
            graph_error = None
            graph_html = None
            graph_stats = {"nodes": 0, "edges": 0}
            try:
                with st.spinner("Building interactive knowledge graph…"):
                    graph = build_knowledge_graph(result.get("title", "Research paper"), analysis)
                    graph_stats = {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}
                    graph_html = save_interactive_graph(graph)
            except Exception as exc:
                graph_error = f"{type(exc).__name__}: {exc}"
            progress.progress(100, text="Analysis complete")
            st.session_state.paper_result = result
            st.session_state.paper_analysis = analysis
            st.session_state.paper_graph_html = graph_html
            st.session_state.paper_graph_stats = graph_stats
            st.session_state.paper_graph_error = graph_error
            st.success("Paper analysis completed. Explore the tabs below.")
        except Exception as exc:
            st.error(f"Could not process this PDF: {type(exc).__name__}: {exc}")
        finally:
            if temp_path and temp_path.exists():
                try: temp_path.unlink()
                except OSError: pass

st.markdown("""
<div class="hero">
  <div class="eyebrow">AI-ASSISTED RESEARCH DESK</div>
  <div class="hero-title">Read the paper.<br>Map the ideas.</div>
  <div class="hero-sub">A workspace for exploring research papers through structured metadata, candidate evidence, semantic insights, and interactive concept maps. Treat model outputs as research leads—not verified conclusions.</div>
</div>
""", unsafe_allow_html=True)

result = st.session_state.paper_result
analysis = st.session_state.paper_analysis
graph_html = st.session_state.paper_graph_html

if result is None or analysis is None:
    a, b, c = st.columns(3)
    for col, icon, title, body in [
        (a, "⌕", "Understand", "Review the abstract, paper structure, and extracted text."),
        (b, "✳", "Investigate", "Inspect candidate keywords, problems, methods, and findings."),
        (c, "◎", "Connect", "Explore a graph generated from the paper's extracted concepts."),
    ]:
        with col:
            st.markdown(f'<div class="card"><div style="font-size:28px">{icon}</div><div class="card-title">{title}</div><div class="card-text">{body}</div></div>', unsafe_allow_html=True)
    st.info("Upload a research PDF from the sidebar and select **Analyze paper** to populate your workspace.")
    st.markdown('<div class="footer">PAPERGRAPH · RESEARCH DISCOVERY WORKSPACE</div>', unsafe_allow_html=True)
    st.stop()

title = escape(str(result.get("title") or "Untitled research paper"))
filename = escape(str(result.get("filename") or "Uploaded PDF"))
st.markdown(f'<div class="card"><div class="eyebrow">ACTIVE PAPER</div><div style="font-family:Manrope,sans-serif;font-size:21px;font-weight:800;color:#172033">{title}</div><div class="card-text">{filename}</div></div>', unsafe_allow_html=True)

stats = st.session_state.paper_graph_stats or {}
metrics = [
    ("PAGES", result.get("page_count", 0)),
    ("EXTRACTED CHARACTERS", f'{result.get("total_characters", 0):,}'),
    ("KEYWORDS", len(analysis.get("keywords", []))),
    ("GRAPH NODES / EDGES", f'{stats.get("nodes", 0)} / {stats.get("edges", 0)}'),
]
cols = st.columns(4)
for col, (label, value) in zip(cols, metrics):
    with col:
        st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)

overview_tab, insights_tab, graph_tab, document_tab, export_tab = st.tabs([
    "📄 Overview", "✳ Evidence & insights", "🕸️ Knowledge graph", "☰ Document explorer", "↗ Export"
])

with overview_tab:
    st.markdown('<div class="section-title">Paper overview</div><div class="section-sub">Start with the document’s own framing before reviewing automated suggestions.</div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><div class="card-title">Abstract</div></div>', unsafe_allow_html=True)
    if result.get("abstract"):
        st.write(result["abstract"])
    else:
        st.info("No abstract was detected. Check the extracted document for formatting or heading issues.")
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

with insights_tab:
    st.markdown('<div class="section-title">Evidence & NLP insights</div><div class="section-sub">These are automated candidates. Validate them against the paper before citing or relying on them.</div>', unsafe_allow_html=True)
    keywords = analysis.get("keywords", [])
    st.markdown("#### Candidate keywords")
    if keywords:
        st.markdown("".join(f'<span class="pill">{escape(str(word))}</span>' for word in keywords), unsafe_allow_html=True)
    else:
        st.info("No keywords found. The abstract or extracted text may be too short.")
    groups = [
        ("Research problem / gap candidates", "research_problem_candidates", "What problem or gap might the paper address?"),
        ("Method candidates", "method_candidates", "Which methods or approaches appear relevant?"),
        ("Result candidates", "result_candidates", "Which sentences may describe findings?"),
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
    st.warning("PaperGraph currently ranks sentences by semantic similarity; it does not prove that a sentence is a true research gap, method, or result.")

with graph_tab:
    st.markdown('<div class="section-title">Knowledge graph</div><div class="section-sub">Explore entities and candidate relationships extracted from this paper. Drag nodes, zoom, and hover for details.</div>', unsafe_allow_html=True)
    if st.session_state.paper_graph_error:
        st.error("The graph could not be generated.")
        st.code(st.session_state.paper_graph_error)
    elif graph_html:
        st.caption(f'{stats.get("nodes", 0)} nodes · {stats.get("edges", 0)} relationships')
        components.html(graph_html, height=680, scrolling=True)
        st.download_button("Download interactive graph (HTML)", data=graph_html.encode("utf-8"), file_name="papergraph-knowledge-graph.html", mime="text/html", use_container_width=True)
        st.caption("If downloaded, open the HTML file in a modern browser. The graph is generated from the current paper only.")
    else:
        st.warning("No graph HTML is available. Re-analyze the paper and check the error details if this persists.")
    with st.expander("How to interpret this graph"):
        st.write("Nodes represent the paper, candidate problem/method/finding sentences, and extracted keywords. Edges show the graph structure created by PaperGraph; they are not proof that the linked concepts have a causal or scientifically validated relationship.")

with document_tab:
    st.markdown('<div class="section-title">Document explorer</div><div class="section-sub">Inspect extracted text page by page. Always compare important passages with the original PDF.</div>', unsafe_allow_html=True)
    query = st.text_input("Search extracted text", placeholder="Search for a term, method, dataset, metric…")
    pages = result.get("pages", [])
    matching = []
    for page in pages:
        page_text = page.get("text", "")
        if not query or query.casefold() in page_text.casefold():
            matching.append(page)
    st.caption(f"{len(matching)} of {len(pages)} pages shown")
    for page in matching:
        with st.expander(f'Page {page.get("page", "?")} · {page.get("characters", len(page.get("text", "")))} characters'):
            if page.get("text"):
                st.text(page["text"])
            else:
                st.warning("No extractable text on this page.")
    if query and not matching:
        st.info("No matching pages. Try a shorter search term.")

with export_tab:
    st.markdown('<div class="section-title">Export research notes</div><div class="section-sub">Download structured outputs for your own review and literature workflow.</div>', unsafe_allow_html=True)
    bundle = {"document": {k: result.get(k) for k in ("filename", "title", "abstract", "sections", "page_count", "total_characters", "is_likely_scanned")}, "analysis": analysis, "graph": stats, "notice": "Automated outputs are candidates and require verification against the source paper."}
    st.download_button("Download analysis bundle (JSON)", data=json.dumps(bundle, ensure_ascii=False, indent=2), file_name="papergraph-analysis.json", mime="application/json", use_container_width=True)
    extraction = json.dumps(result, ensure_ascii=False, indent=2)
    st.download_button("Download full extracted text (JSON)", data=extraction, file_name="papergraph-extraction.json", mime="application/json", use_container_width=True)
    md = [f"# {result.get('title', 'Research paper')}", "", f"**File:** {result.get('filename', '')}", "", "## Abstract", "", result.get("abstract") or "No abstract detected.", "", "## Candidate keywords", ""]
    md += [f"- {x}" for x in analysis.get("keywords", [])]
    for heading, key in [("Research problem / gap candidates", "research_problem_candidates"), ("Method candidates", "method_candidates"), ("Result candidates", "result_candidates")]:
        md += ["", f"## {heading}", ""]
        md += [f"- {x}" for x in analysis.get(key, [])] or ["- No candidates found."]
    md += ["", "> Note: These are automated candidates. Verify claims against the original PDF."]
    st.download_button("Download research notes (Markdown)", data="\n".join(md), file_name="papergraph-research-notes.md", mime="text/markdown", use_container_width=True)

st.markdown('<div class="footer">PAPERGRAPH · READ CAREFULLY · VERIFY EVIDENCE · CONNECT IDEAS</div>', unsafe_allow_html=True)
