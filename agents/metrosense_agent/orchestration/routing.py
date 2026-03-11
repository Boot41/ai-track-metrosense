from __future__ import annotations

from dataclasses import dataclass

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
SCORECARD_KEYWORDS = {"risk", "scorecard", "vulnerability", "assessment", "how vulnerable is"}


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
