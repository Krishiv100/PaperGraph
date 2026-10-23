
from pathlib import Path
import re

import pymupdf


# Common section headings found in research papers.
SECTION_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(abstract|introduction|background|related work|"
    r"literature review|methodology|methods|proposed method|"
    r"experiments|experimental setup|results|discussion|"
    r"conclusion|limitations|references|acknowledgements|"
    r"acknowledgments)\s*[:.]?\s*$",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""
    text = text.replace("\x00", "")
    text = re.sub(r"-\s*\n\s*(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_title(first_page_text: str, metadata_title: str) -> str:
    """Use PDF metadata first, then estimate the title from page one."""
    if metadata_title and metadata_title.strip():
        return metadata_title.strip()

    lines = [
        line.strip()
        for line in first_page_text.splitlines()
        if line.strip()
    ]

    for line in lines[:15]:
        if len(line) < 12 or len(line) > 250:
            continue
        if SECTION_PATTERN.match(line):
            continue
        if line.lower().startswith(
            ("arxiv:", "doi:", "abstract", "preprint")
        ):
            continue

        return line

    return "Title not detected"


def detect_abstract(pages: list[dict]) -> str:
    """Extract text after the Abstract heading until another section."""
    collected = []
    started = False

    for page in pages:
        for line in page["text"].splitlines():
            stripped = line.strip()

            if not started:
                # Handle 'Abstract' on its own line.
                if re.match(r"^abstract\s*[:.]?$", stripped, re.I):
                    started = True
                    continue

                # Handle 'Abstract: Text begins here' on one line.
                match = re.match(
                    r"^abstract\s*[:.]?\s+(.+)$",
                    stripped,
                    re.I,
                )
                if match:
                    collected.append(match.group(1))
                    started = True
                continue

            # Stop when a new recognized section begins.
            if SECTION_PATTERN.match(stripped):
                return clean_text("\n".join(collected))

            collected.append(stripped)

    return clean_text("\n".join(collected))


def detect_sections(pages: list[dict]) -> list[dict]:
    """Find common section headings and their page numbers."""
    sections = []

    for page in pages:
        for line in page["text"].splitlines():
            heading = line.strip()

            if SECTION_PATTERN.match(heading):
                sections.append({
                    "heading": heading,
                    "page": page["page"],
                })

    return sections


def extract_pdf(pdf_path: str | Path) -> dict:
    """Extract text and basic metadata from a research paper PDF."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("The uploaded file must be a PDF.")

    pages = []

    with pymupdf.open(pdf_path) as document:
        if document.needs_pass:
            raise ValueError("This PDF is password-protected.")

        metadata = document.metadata or {}

        for page_number, page in enumerate(document, start=1):
            text = clean_text(page.get_text("text", sort=True))

            pages.append({
                "page": page_number,
                "text": text,
                "characters": len(text),
            })

        metadata_title = metadata.get("title") or ""

    first_page_text = pages[0]["text"] if pages else ""

    full_text = "\n\n".join(
        f"[Page {page['page']}]\n{page['text']}"
        for page in pages
        if page["text"]
    )

    total_characters = sum(
        page["characters"] for page in pages
    )

    return {
        "filename": pdf_path.name,
        "title": detect_title(first_page_text, metadata_title),
        "abstract": detect_abstract(pages),
        "sections": detect_sections(pages),
        "pages": pages,
        "full_text": full_text,
        "page_count": len(pages),
        "total_characters": total_characters,
        "is_likely_scanned": (
            bool(pages)
            and total_characters / len(pages) < 80
        ),
    }
