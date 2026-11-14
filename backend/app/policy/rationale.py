"""One-line reason for a drafted rebooking, from a template (AGENTS.md §11.5).

Every number and flight number in the sentence is a field of the draft; nothing is free text.
"""

from __future__ import annotations

from datetime import datetime

PREFERENCE_TEXT = {
    "earliest_arrival": "the earliest arrival",
    "keep_cabin": "to keep the same cabin",
    "rest_first": "to rest before flying on",
    "unset": "no stated preference",
}
CABIN_NAMES = {"F": "First", "J": "Business", "W": "Premium Economy", "Y": "Economy"}


def group_text(size: int) -> str:
    return "travelling alone" if size == 1 else f"group of {size}"


def rationale(*, name: str, cabin: str, group_size: int, p_miss: float, out_flight: str,
              driver_text: str | None, alt_flight: str, alt_dep: datetime,
              alt_arrival: datetime | None, preference: str) -> str:
    parts = [f"{name} ({CABIN_NAMES.get(cabin, cabin)}, {group_text(group_size)}): "
             f"{p_miss:.0%} likely to miss {out_flight}."]
    if driver_text:
        parts.append(f"{driver_text}.")
    backup = f"Backup held on {alt_flight} {alt_dep:%H:%M}"
    if alt_arrival:
        backup += f", arrives {alt_arrival:%H:%M}"
    parts.append(backup + ".")
    parts.append(f"Prefers {PREFERENCE_TEXT.get(preference, preference)}.")
    return " ".join(parts)
