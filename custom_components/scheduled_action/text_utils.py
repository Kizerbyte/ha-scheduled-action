from __future__ import annotations

import re
import unicodedata


def normalize_label(value: str | None) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    return value[0].upper() + value[1:]


def strip_trigger_suffix(label: str | None) -> str:
    value = normalize_label(label)
    if not value:
        return ""
    lowered = value.lower()
    separators = [" in ", " when ", " on "]
    cut_positions = [lowered.find(sep) for sep in separators if lowered.find(sep) > 0]
    if cut_positions:
        return value[: min(cut_positions)].strip()
    return value


def normalize_trigger_label(value: str | None) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    return value.replace("_", " ").lower()


def format_action_key(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    return value.replace("_", " ").capitalize()


def format_trigger_type(value: str) -> str:
    value = str(value).strip()
    if not value:
        return ""
    return value.replace("_", " ").capitalize()


def sort_normalized_label(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", normalize_label(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"\s+", " ", ascii_value).strip().casefold()
    return collapsed
