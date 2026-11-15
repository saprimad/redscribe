"""Stable speaker-label colours shared by the UI and research exports."""
import hashlib
import re

# Dark colours remain legible on white; IDs 00-07 have distinct accents.
SPEAKER_PALETTE = (
    "8E1235", "2458A6", "24735B", "8C4E12",
    "7040A0", "00727D", "A33E00", "5D497C",
)
UNKNOWN_COLOUR = "667085"


def speaker_colour(speaker: str | None) -> str:
    """Return six-digit RGB, independent of encounter order or report sorting."""
    label = (speaker or "UNKNOWN").strip().upper()
    if not label or label == "UNKNOWN":
        return UNKNOWN_COLOUR
    match = re.fullmatch(r"SPEAKER[_\s-]*(\d+)", label)
    index = int(match.group(1)) if match else int.from_bytes(
        hashlib.sha256(label.encode("utf-8")).digest()[:4], "big"
    )
    return SPEAKER_PALETTE[index % len(SPEAKER_PALETTE)]


def speaker_fill(speaker: str | None) -> str:
    """A pale version of the accent for an Excel speaker cell."""
    colour = speaker_colour(speaker)
    return "".join(f"{round(int(colour[i:i+2], 16) * 0.10 + 255 * 0.90):02X}"
                   for i in (0, 2, 4))
