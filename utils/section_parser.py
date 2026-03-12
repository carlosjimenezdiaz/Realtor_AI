from __future__ import annotations

SECTION_MARKER = "---SECCIÓN:"
SECTION_END = "---"


def parse_sections(text: str) -> list[tuple[str, str]]:
    """
    Parses ---SECCIÓN: NAME--- markers from a Claude response.
    Returns an ordered list of (name, content) tuples.
    Used by WritingAgent and EditorialAgent.
    """
    result: list[tuple[str, str]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith(SECTION_MARKER):
            if current_name is not None:
                result.append((current_name, "\n".join(current_lines).strip()))
            current_name = (
                stripped
                .replace(SECTION_MARKER, "")
                .rstrip(SECTION_END)
                .strip()
            )
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        result.append((current_name, "\n".join(current_lines).strip()))

    return result
