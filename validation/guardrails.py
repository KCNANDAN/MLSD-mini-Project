import re
from typing import Any


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?prior\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"reveal\s+(your\s+)?(system|developer)\s+prompt",
    r"show\s+(me\s+)?(your\s+)?hidden\s+instructions",
    r"act\s+as\s+(an?\s+)?unrestricted",
    r"bypass\s+(all\s+)?safety",
    r"override\s+(all\s+)?(rules|instructions|restrictions)",
]


def inspect_petition(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Inspect petition text for common prompt-injection indicators.

    A flagged petition is not automatically rejected.
    It must be quarantined or escalated for review by the caller.
    """
    text_parts = [
        str(payload.get("description", "")),
        str(payload.get("additional_details", "")),
    ]

    combined_text = " ".join(text_parts)

    matched_patterns = []

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, combined_text, flags=re.IGNORECASE):
            matched_patterns.append(pattern)

    return {
        "safe": len(matched_patterns) == 0,
        "flagged": len(matched_patterns) > 0,
        "reason": (
            "Potential prompt injection detected"
            if matched_patterns
            else None
        ),
        "matched_pattern_count": len(matched_patterns),
    }