from __future__ import annotations

from dataclasses import dataclass
import re

FLOOD_KEYWORDS = {
    "flood",
    "rain",
    "inundation",
    "drainage",
    "lake",
    "waterlogging",
    "barricade",
}
HEAT_KEYWORDS = {
    "aqi",
    "air quality",
    "heat",
    "uhi",
    "pollution",
    "pm2.5",
    "pm10",
    "no2",
}
INFRA_KEYWORDS = {
    "power",
    "outage",
    "grid",
    "bescom",
    "tree fall",
    "wind",
}
LOGISTICS_KEYWORDS = {
    "traffic",
    "corridor",
    "delay",
    "route",
    "logistics",
    "orr",
    "hosur",
}
SCORECARD_KEYWORDS = {
    "risk",
    "scorecard",
    "vulnerability",
    "assessment",
    "how vulnerable is",
}
GREETING_PHRASES = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "namaste",
}
GREETING_ALLOWED_TOKENS = {
    "hi",
    "hello",
    "hey",
    "good",
    "morning",
    "afternoon",
    "evening",
    "namaste",
    "there",
    "team",
    "metrosense",
    "metro",
    "sense",
    "agent",
}


@dataclass(frozen=True)
class IntentClassification:
    flood: bool
    heat: bool
    infra: bool
    logistics: bool


def _matches_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_intents(message: str) -> IntentClassification:
    text = message.lower()
    return IntentClassification(
        flood=_matches_any(text, FLOOD_KEYWORDS),
        heat=_matches_any(text, HEAT_KEYWORDS),
        infra=_matches_any(text, INFRA_KEYWORDS),
        logistics=_matches_any(text, LOGISTICS_KEYWORDS),
    )


def should_trigger_scorecard(message: str) -> bool:
    return _matches_any(message.lower(), SCORECARD_KEYWORDS)


def determine_response_mode(message: str) -> str:
    if should_trigger_scorecard(message):
        return "scorecard"
    return "text"


def _normalize_text(message: str) -> str:
    lowered = message.lower().strip()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return " ".join(cleaned.split())


def is_greeting_only(message: str) -> bool:
    normalized = _normalize_text(message)
    if not normalized:
        return False

    if normalized in GREETING_PHRASES:
        return True

    # If query intent words exist, this is not greeting-only.
    if _matches_any(
        normalized, FLOOD_KEYWORDS | HEAT_KEYWORDS | INFRA_KEYWORDS | LOGISTICS_KEYWORDS
    ):
        return False
    if _matches_any(normalized, SCORECARD_KEYWORDS):
        return False

    tokens = set(normalized.split())
    contains_greeting_token = any(
        token in GREETING_ALLOWED_TOKENS for token in tokens
    ) and (
        "hi" in tokens
        or "hello" in tokens
        or "hey" in tokens
        or "namaste" in tokens
        or (
            "good" in tokens
            and ("morning" in tokens or "afternoon" in tokens or "evening" in tokens)
        )
    )
    return contains_greeting_token and tokens.issubset(GREETING_ALLOWED_TOKENS)
