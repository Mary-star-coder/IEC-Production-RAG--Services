
import re
from pathlib import Path

from app.config import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE


# ---------------------------------------------------------
# QUESTION VALIDATION SETTINGS
# ---------------------------------------------------------

# Maximum number of characters accepted in a user question.
MAX_QUESTION_LENGTH = 1000


# ---------------------------------------------------------
# PROMPT INJECTION DETECTION PATTERNS
# ---------------------------------------------------------

# Common instruction-manipulation phrases.
# These patterns provide basic protection, not complete security.
BLOCKED_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?(previous\s+)?instructions",
    r"forget\s+(all\s+)?(previous\s+)?instructions",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"show\s+(me\s+)?(your\s+)?system\s+prompt",
    r"reveal\s+hidden\s+instructions",
    r"ignore\s+your\s+rules",
    r"bypass\s+(your\s+)?(safety\s+)?(rules|instructions|guardrails)",
    r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions",
    r"developer\s+message",
]

# Compile patterns once to avoid recompiling them for every request.
COMPILED_BLOCKED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in BLOCKED_PATTERNS
]


# ---------------------------------------------------------
# QUESTION VALIDATION
# ---------------------------------------------------------

def validate_question(question: str) -> bool:
    """
    Validate question length and detect common prompt-injection phrases.

    Args:
        question: User-provided question.

    Returns:
        True if the question passes basic validation; otherwise False.
    """

    # Reject missing, empty, or whitespace-only input.
    if not isinstance(question, str) or not question.strip():
        return False

    # Reject questions exceeding the configured character limit.
    if len(question) > MAX_QUESTION_LENGTH:
        return False

    # Normalize whitespace before checking suspicious instructions.
    normalized_question = " ".join(question.split())

    # Reject questions containing known prompt-injection patterns.
    return not any(
        pattern.search(normalized_question)
        for pattern in COMPILED_BLOCKED_PATTERNS
    )


# ---------------------------------------------------------
# DOCUMENT UPLOAD VALIDATION
# ---------------------------------------------------------

def validate_upload(filename: str, file_size: int) -> bool:
    """
    Validate uploaded document filename, extension, and size.

    Args:
        filename: Original uploaded filename.
        file_size: Uploaded file size in bytes.

    Returns:
        True if basic upload validation passes; otherwise False.
    """

    # Reject missing or invalid filenames.
    if not isinstance(filename, str) or not filename.strip():
        return False

    # Reject invalid file sizes.
    if not isinstance(file_size, int) or file_size <= 0:
        return False

    # Extract the extension safely and normalize it.
    extension = Path(filename).suffix.lower()

    # Reject files without an extension.
    if not extension:
        return False

    # Reject file formats not supported by the ingestion pipeline.
    if extension not in SUPPORTED_EXTENSIONS:
        return False

    # Accept only files within the configured upload size limit.
    return file_size <= MAX_FILE_SIZE
