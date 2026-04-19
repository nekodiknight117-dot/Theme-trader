"""Normalize risk and parse interest tags for overlap-focused prompts."""


def normalize_risk(risk: str) -> str:
    """Map user profile values to low | medium | high."""
    if not risk or not str(risk).strip():
        return "medium"
    m = str(risk).strip().lower()
    if m in ("low", "medium", "high"):
        return m
    return "medium"


def interest_tags(interests: str) -> list[str]:
    """Split comma/semicolon-separated interests into unique, trimmed tags (order preserved)."""
    if not interests or not str(interests).strip():
        return []
    parts = str(interests).replace(";", ",").split(",")
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        t = p.strip()
        if not t:
            continue
        key = t.lower()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out
