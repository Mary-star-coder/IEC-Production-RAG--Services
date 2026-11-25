
# Regular expressions are used to detect known prompt-injection phrases.
import re

# Import upload validation settings from the central configuration.
from app.config import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE


# ---------------------------------------------------------
# PROMPT INJECTION DETECTION PATTERNS
# ---------------------------------------------------------

# Common instruction-manipulation phrases that should be blocked.
# These patterns provide basic input protection, not complete
# protection against every possible prompt-injection technique.
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


# ---------------------------------------------------------
# QUESTION VALIDATION
# ---------------------------------------------------------

def validate_question(question: str) -> bool:
    """
    Check whether a question contains known prompt-injection phrases.

    Args:
        question: User-provided question.

    Returns:
        True if no blocked pattern is detected; otherwise False.
    """

    # Convert the question to lowercase for case-insensitive matching.
    normalized_question = question.lower()

    # Reject the question if any blocked pattern is found.
    return not any(
        re.search(pattern, normalized_question)
        for pattern in BLOCKED_PATTERNS
    )


# ---------------------------------------------------------
# DOCUMENT UPLOAD VALIDATION
# ---------------------------------------------------------

def validate_upload(filename: str, file_size: int) -> bool:
    """
    Validate uploaded document extension and file size.

    Args:
        filename: Original name of the uploaded file.
        file_size: Size of the uploaded file in bytes.

    Returns:
        True if the file format and size are allowed;
        otherwise False.
    """

    # Extract the file extension and normalize it to lowercase.
    extension = "." + filename.lower().rsplit(".", 1)[-1]

    # Reject filenames without a file extension.
    if "." not in filename:
        return False

    # Reject formats that are not supported by the application.
    if extension not in SUPPORTED_EXTENSIONS:
        return False

    # Accept only non-empty files within the configured size limit.
    return 0 < file_size <= MAX_FILE_SIZE
