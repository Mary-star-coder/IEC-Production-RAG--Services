
# Path provides cross-platform file path handling.
from pathlib import Path

# Import libraries for extracting text from supported document formats.
from docx import Document
from pptx import Presentation
from pypdf import PdfReader


# File formats supported by the document loading pipeline.
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


# ---------------------------------------------------------
# DOCUMENT TEXT EXTRACTION
# ---------------------------------------------------------

def load_document(file_path: str) -> list[dict]:
    """
    Extract text and source metadata from a supported document.

    Supported formats:
        PDF: Extract text page by page.
        DOCX: Extract text from paragraphs.
        PPTX: Extract text from individual slides.
        TXT/MD: Read the complete text file.

    Args:
        file_path: Path to the uploaded document.

    Returns:
        A list of dictionaries containing extracted text
        and its corresponding page or slide number.

    Raises:
        ValueError: If the format is unsupported or no extractable
        text is found in the document.
    """

    # Convert the supplied file path into a Path object.
    path = Path(file_path)

    # Normalize the extension to lowercase for reliable validation.
    extension = path.suffix.lower()

    # Reject unsupported document formats.
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {extension}")

    # Store extracted text and its original source location.
    pages = []

    # -----------------------------------------------------
    # PDF TEXT EXTRACTION
    # -----------------------------------------------------
    if extension == ".pdf":
        reader = PdfReader(str(path))

        # Extract text separately from each PDF page.
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            # Ignore pages that contain no extractable text.
            if text.strip():
                pages.append({
                    "text": text,
                    "page": page_number,
                })

    # -----------------------------------------------------
    # DOCX TEXT EXTRACTION
    # -----------------------------------------------------
    elif extension == ".docx":
        document = Document(str(path))

        # Extract non-empty paragraphs and combine them into one text block.
        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

        # Store extracted DOCX text with a default page reference.
        if text.strip():
            pages.append({"text": text, "page": 1})

    # -----------------------------------------------------
    # PPTX TEXT EXTRACTION
    # -----------------------------------------------------
    elif extension == ".pptx":
        presentation = Presentation(str(path))

        # Process each presentation slide independently.
        for slide_number, slide in enumerate(
            presentation.slides, start=1
        ):
            # Extract text from shapes that contain text frames.
            text = "\n".join(
                shape.text
                for shape in slide.shapes
                if shape.has_text_frame and shape.text.strip()
            )

            # Preserve the original slide number as source metadata.
            if text.strip():
                pages.append({
                    "text": text,
                    "page": slide_number,
                })

    # -----------------------------------------------------
    # TXT AND MARKDOWN TEXT EXTRACTION
    # -----------------------------------------------------
    else:
        # Read plain-text content using UTF-8 encoding.
        text = path.read_text(encoding="utf-8")

        if text.strip():
            pages.append({"text": text, "page": 1})

    # Reject documents that produce no usable text.
    if not pages:
        raise ValueError("The document contains no extractable text.")

    # Return extracted text together with source location metadata.
    return pages
