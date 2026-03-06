from __future__ import annotations
MAX_CHARS = 3800  # Telegram limit is 4096; buffer for safety


def split_for_telegram(text: str) -> list[str]:
    """
    Splits text into Telegram-safe chunks (≤ MAX_CHARS).
    Splits at newlines to avoid cutting sentences mid-way.
    """
    if len(text) <= MAX_CHARS:
        return [text]

    chunks: list[str] = []
    lines = text.split("\n")
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for the newline
        if current_len + line_len > MAX_CHARS:
            if current:
                chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks
