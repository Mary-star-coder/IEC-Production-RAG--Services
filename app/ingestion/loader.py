
# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

from pathlib import Path

from docx import Document
from pptx import Presentation
from pypdf import PdfReader


# File types accepted by the document ingestion pipeline.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


# ---------------------------------------------------------
# DOCUMENT TEXT EXTRACTION
# ---------------------------------------------------------

def load_document(file_path: str) -> list[dict]:
    """
    Extract text from supported document formats.

    PDF:
        Extracts text page by page.

    DOCX:
        Extracts paragraphs and table contents.
        DOCX does not provide reliable physical page numbers through
        python-docx, so extracted content uses page=1 as a reference.

    PPTX:
        Extracts text from individual slides, including tables.

    TXT/MD:
        Extracts the complete UTF-8 text file as page=1.

    Returns:
        List of dictionaries containing text and page/slide metadata.

    Raises:
        ValueError: For missing, unsupported, encrypted, corrupt,
                    or text-empty documents.
    """

    path = Path(file_path)

    # Check that the file exists and is a regular file.
    if not path.exists() or not path.is_file():
        raise ValueError("The uploaded document could not be found.")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {extension}")

    pages = []

    try:
        # -------------------------------------------------
        # PDF EXTRACTION
        # -------------------------------------------------
        if extension == ".pdf":
            reader = PdfReader(str(path), strict=False)

            # Encrypted PDFs cannot be processed without a password.
            if reader.is_encrypted:
                raise ValueError("Encrypted PDF documents are not supported.")

            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""

                if text.strip():
                    pages.append({
                        "text": text.strip(),
                        "page": page_number,
                    })

        # -------------------------------------------------
        # DOCX EXTRACTION
        # -------------------------------------------------
        elif extension == ".docx":
            document = Document(str(path))
            content_parts = []

            # Extract regular paragraphs.
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text.strip())

            # Extract table contents, which may contain important data.
            for table in document.tables:
                for row in table.rows:
                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                        if cell.text.strip()
                    ]

                    if cells:
                        content_parts.append(" | ".join(cells))

            combined_text = "\n".join(content_parts)

            if combined_text.strip():
                # python-docx does not expose reliable rendered page numbers.
                pages.append({
                    "text": combined_text,
                    "page": 1,
                })

        # -------------------------------------------------
        # PPTX EXTRACTION
        # -------------------------------------------------
        elif extension == ".pptx":
            presentation = Presentation(str(path))

            for slide_number, slide in enumerate(
                presentation.slides,
                start=1,
            ):
                slide_parts = []

                for shape in slide.shapes:
                    # Extract text from normal text shapes.
                    if shape.has_text_frame and shape.text.strip():
                        slide_parts.append(shape.text.strip())

                    # Extract table cells separately.
                    if shape.has_table:
                        for row in shape.table.rows:
                            cells = [
                                cell.text.strip()
                                for cell in row.cells
                                if cell.text.strip()
                            ]

                            if cells:
                                slide_parts.append(" | ".join(cells))

                slide_text = "\n".join(slide_parts)

                if slide_text.strip():
                    pages.append({
                        "text": slide_text,
                        "page": slide_number,
                    })

        # -------------------------------------------------
        # TXT AND MARKDOWN EXTRACTION
        # -------------------------------------------------
        else:
            # UTF-8 decoding errors are reported as invalid documents.
            text = path.read_text(encoding="utf-8")

            if text.strip():
                pages.append({
                    "text": text.strip(),
                    "page": 1,
                })

    except ValueError:
        # Preserve intentional validation errors.
        raise

    except Exception as exc:
        # Convert parser and decoding errors into a clear ingestion error.
        raise ValueError(
            "The document is corrupt, invalid, or cannot be processed."
        ) from exc

    # Reject image-only PDFs and other files with no extractable text.
    if not pages:
        raise ValueError("The document contains no extractable text.")

    return pages
