
import json
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pdf_ingestion import extract_pdf
from paper_analysis import analyze_paper
from knowledge_graph import build_knowledge_graph, save_interactive_graph


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="PaperGraph | Research Intelligence",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# CUSTOM UI DESIGN
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background: #f5f7fb;
    }

    [data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #273449;
    }

    [data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    .brand {
        font-family: 'Manrope', sans-serif;
        font-size: 27px;
        font-weight: 800;
        letter-spacing: -1.2px;
        color: #ffffff;
        padding: 12px 0 2px 0;
    }

    .brand span {
        color: #60a5fa;
    }

    .sidebar-caption {
        font-size: 12px;
        color: #9ca3af;
        margin-bottom: 25px;
    }

    .eyebrow {
        color: #2563eb;
        text-transform: uppercase;
        letter-spacing: 1.8px;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .hero-title {
        font-family: 'Manrope', sans-serif;
        color: #111827;
        font-size: clamp(28px, 4vw, 40px);
        line-height: 1.15;
        letter-spacing: -1.5px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .hero-description {
        color: #64748b;
        font-size: 15px;
        line-height: 1.7;
        margin-bottom: 24px;
    }

    .section-title {
        font-family: 'Manrope', sans-serif;
        color: #111827;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-top: 12px;
        margin-bottom: 5px;
    }

    .section-description {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 18px;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 15px;
        padding: 20px;
        min-height: 112px;
    }

    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #64748b;
        margin-bottom: 10px;
    }

    .metric-value {
        font-family: 'Manrope', sans-serif;
        font-size: 27px;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.8px;
    }

    .panel {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 16px;
    }

    .panel-title {
        color: #111827;
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .panel-text {
        color: #475569;
        font-size: 14px;
        line-height: 1.75;
    }

    .tag {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        padding: 6px 10px;
        border-radius: 8px;
        margin: 4px 4px 4px 0;
        font-size: 12px;
        font-weight: 600;
    }

    .footer {
        color: #94a3b8;
        font-size: 12px;
        text-align: center;
        padding: 28px 0 12px 0;
    }

    div.stButton > button[kind="primary"] {
        background: #2563eb;
        border: 1px solid #2563eb;
        color: white;
        border-radius: 10px;
        min-height: 46px;
        font-weight: 700;
        width: 100%;
    }

    div.stButton > button[kind="primary"]:hover {
        background: #1d4ed8;
        border-color: #1d4ed8;
    }

    div[data-testid="stFileUploader"] {
        background: #ffffff;
        border: 1px dashed #93b4e8;
        border-radius: 12px;
        padding: 8px;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
    }

    [data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 10px;
    }

    #MainMenu, footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "paper_result" not in st.session_state:
    st.session_state.paper_result = None

if "paper_analysis" not in st.session_state:
    st.session_state.paper_analysis = None

if "paper_graph_html" not in st.session_state:
    st.session_state.paper_graph_html = None


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="brand">Paper<span>Graph</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="sidebar-caption">RESEARCH INTELLIGENCE WORKSPACE</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Your workspace")
    st.caption("Turn research papers into structured insights.")

    uploaded_file = st.file_uploader(
        "Upload a research paper",
        type=["pdf"],
        help="Choose a text-based PDF up to 25 MB.",
    )

    if uploaded_file is not None:
        st.caption(
            f"Selected file: {uploaded_file.name}"
        )

    process_clicked = st.button(
        "✦  Analyze research paper",
        type="primary",
        disabled=uploaded_file is None,
        use_container_width=True,
    )

    st.divider()

    st.markdown("**WORKSPACE SECTIONS**")
    st.caption("01  ·  Overview")
    st.caption("02  ·  NLP insights")
    st.caption("03  ·  Knowledge graph")
    st.caption("04  ·  Extracted document")

    st.divider()

    st.markdown("**PROCESSING**")
    st.caption("PDF extraction · Local NLP · Graph generation")
    st.caption("No external AI API key required.")

    if st.button("Clear current analysis", use_container_width=True):
        st.session_state.paper_result = None
        st.session_state.paper_analysis = None
        st.session_state.paper_graph_html = None
        st.rerun()


# --------------------------------------------------
# PROCESS THE PDF
# --------------------------------------------------

if process_clicked and uploaded_file is not None:
    if uploaded_file.size > 25 * 1024 * 1024:
        st.error("This PDF exceeds the 25 MB upload limit.")
    else:
        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".pdf",
                delete=False,
            ) as temporary_file:
                temporary_file.write(uploaded_file.getvalue())
                temporary_path = Path(temporary_file.name)

            with st.spinner("Extracting document text..."):
                result = extract_pdf(temporary_path)

            if result["is_likely_scanned"]:
                st.warning(
                    "This document contains very little extractable text. "
                    "A scanned PDF may require OCR."
                )

            with st.spinner(
                "Analyzing keywords, methods, problems, and findings..."
            ):
                analysis = analyze_paper(result)

            output_dir = Path("outputs")
            output_dir.mkdir(parents=True, exist_ok=True)

            graph_path = output_dir / "papergraph.html"

            with st.spinner("Building the knowledge graph..."):
                graph = build_knowledge_graph(
                    result["title"],
                    analysis,
                )
                save_interactive_graph(graph, str(graph_path))

            st.session_state.paper_result = result
            st.session_state.paper_analysis = analysis
            st.session_state.paper_graph_html = graph_path.read_text(
                encoding="utf-8"
            )

            st.success("Your research paper has been analyzed!")

        except Exception as error:
            st.error(f"Could not process the PDF: {error}")

        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()


# --------------------------------------------------
# MAIN HEADER
# --------------------------------------------------

st.markdown(
    '<div class="eyebrow">YOUR AI-ASSISTED RESEARCH DESK</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-title">Understand research.<br>'
    'Discover connections.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-description">'
    'Extract important information from research papers, explore '
    'key findings, and visualize ideas in an interactive knowledge graph.'
    '</div>',
    unsafe_allow_html=True,
)


# --------------------------------------------------
# EMPTY STATE
# --------------------------------------------------

result = st.session_state.paper_result
analysis = st.session_state.paper_analysis
graph_html = st.session_state.paper_graph_html

if result is None or analysis is None:
    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">Welcome to your research workspace</div>
            <div class="panel-text">
                Start by uploading a research paper PDF in the sidebar.
                PaperGraph will extract its text, identify candidate keywords
                and findings, and create a compact knowledge graph.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### What you can explore")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="panel">
                <div style="font-size:26px">⌕</div>
                <div class="panel-title">Paper overview</div>
                <div class="panel-text">
                    Review document metadata, abstract, and section structure.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="panel">
                <div style="font-size:26px">✳</div>
                <div class="panel-title">NLP insights</div>
                <div class="panel-text">
                    Explore keywords and candidate research problems,
                    methods, and findings.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="panel">
                <div style="font-size:26px">◎</div>
                <div class="panel-title">Knowledge graph</div>
                <div class="panel-text">
                    See a compact visual map of a paper and its concepts.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="footer">PAPERGRAPH · RESEARCH WORKSPACE</div>',
        unsafe_allow_html=True,
    )

    st.stop()


# --------------------------------------------------
# DASHBOARD METRICS
# --------------------------------------------------

st.markdown("### Research overview")

metric1, metric2, metric3, metric4 = st.columns(4)

metrics = [
    (metric1, "DOCUMENT PAGES", result["page_count"]),
    (metric2, "EXTRACTED CHARACTERS", f'{result["total_characters"]:,}'),
    (metric3, "KEY CONCEPTS", len(analysis.get("keywords", []))),
    (
        metric4,
        "GRAPH CONNECTIONS",
        max(
            0,
            (len(analysis.get("keywords", [])[:3]))
            + bool(analysis.get("method_candidates"))
            + bool(analysis.get("research_problem_candidates"))
            + bool(analysis.get("result_candidates")),
        ),
    ),
]

for column, label, value in metrics:
    with column:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# DOCUMENT IDENTITY
# --------------------------------------------------

st.markdown("")

st.markdown(
    f"""
    <div class="panel">
        <div class="eyebrow">CURRENT DOCUMENT</div>
        <div class="panel-title">{result["title"]}</div>
        <div class="panel-text">{result["filename"]}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# TABBED WORKSPACE
# --------------------------------------------------

overview_tab, insights_tab, graph_tab, document_tab = st.tabs(
    [
        "📄  Paper overview",
        "✳  NLP insights",
        "◎  Knowledge graph",
        "☰  Extracted document",
    ]
)


# --------------------------------------------------
# OVERVIEW TAB
# --------------------------------------------------

with overview_tab:
    st.markdown(
        '<div class="section-title">Paper overview</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'Review the document summary and structure.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="panel"><div class="panel-title">Abstract</div>',
        unsafe_allow_html=True,
    )

    if result["abstract"]:
        st.write(result["abstract"])
    else:
        st.info("No abstract was detected automatically.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### Section structure")

    if result["sections"]:
        st.dataframe(
            result["sections"],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No recognized section headings were found.")

    if result["is_likely_scanned"]:
        st.warning(
            "This PDF may be scanned. OCR has not been implemented yet."
        )


# --------------------------------------------------
# NLP INSIGHTS TAB
# --------------------------------------------------

with insights_tab:
    st.markdown(
        '<div class="section-title">NLP insights</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'Model-generated candidates to help you review the paper faster. '
        'These are not guaranteed to be correct.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Important keywords")

    keywords = analysis.get("keywords", [])

    if keywords:
        tags_html = "".join(
            f'<span class="tag">{keyword}</span>'
            for keyword in keywords
        )
        st.markdown(tags_html, unsafe_allow_html=True)
    else:
        st.info("No keywords were extracted.")

    insight_groups = [
        (
            "Research problem / gap",
            "research_problem_candidates",
        ),
        ("Methods", "method_candidates"),
        ("Main result candidates", "result_candidates"),
    ]

    for heading, key in insight_groups:
        st.markdown(f"#### {heading}")

        candidates = analysis.get(key, [])

        if candidates:
            for index, sentence in enumerate(candidates, start=1):
                with st.container(border=True):
                    st.caption(f"CANDIDATE {index}")
                    st.write(sentence)
        else:
            st.info("No candidates were found for this category.")


# --------------------------------------------------
# KNOWLEDGE GRAPH TAB
# --------------------------------------------------

with graph_tab:
    st.markdown(
        '<div class="section-title">Knowledge graph</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'Explore the paper and its key concepts. Hover over nodes for details.'
        '</div>',
        unsafe_allow_html=True,
    )

    if graph_html:
        components.html(
            graph_html,
            height=540,
            scrolling=False,
        )

        st.download_button(
            "Download interactive graph",
            data=graph_html.encode("utf-8"),
            file_name="papergraph.html",
            mime="text/html",
            use_container_width=True,
            key="download_graph",
        )
    else:
        st.info("No graph is available. Analyze a paper first.")


# --------------------------------------------------
# EXTRACTED DOCUMENT TAB
# --------------------------------------------------

with document_tab:
    st.markdown(
        '<div class="section-title">Extracted document</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'Inspect extracted text page by page or download the structured data.'
        '</div>',
        unsafe_allow_html=True,
    )

    for page in result["pages"]:
        with st.expander(f'Page {page["page"]}'):
            if page["text"]:
                st.text(page["text"])
            else:
                st.warning("No extractable text on this page.")

    json_data = json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
    )

    st.download_button(
        "Download extracted data (JSON)",
        data=json_data,
        file_name="papergraph_extraction.json",
        mime="application/json",
        use_container_width=True,
        key="download_json",
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    '<div class="footer">'
    'PAPERGRAPH · BUILT FOR RESEARCH DISCOVERY'
    '</div>',
    unsafe_allow_html=True,
)
