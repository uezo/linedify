from typing import Optional


def normalize_line_breaks(text: Optional[str]) -> Optional[str]:
    """Normalize CRLF/CR line endings to LF while preserving None."""
    if text is None:
        return None
    # Replace CRLF first to avoid double replacement, then lone CR
    return text.replace("\r\n", "\n").replace("\r", "\n")
