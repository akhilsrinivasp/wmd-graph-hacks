"""Claude integration (optional).

Used for two things:
  1. parse_order: turn a free-text order into a structured prescription.
  2. summarize: write a short plain-English brief for the pharmacist from the
     facts the agents already put in the graph.

Clinical decisions (base choice, dose checks, interactions) are never made by
the model; they come from graph queries. The app works without an API key.
"""
import json
import os
from typing import Literal, Optional

from pydantic import BaseModel, Field

MODEL = os.getenv("COMPOUNDER_MODEL", "claude-opus-5-5")
# Server-side refusal fallback: if the model declines, the API retries on a
# fallback model chosen by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


class ParsedOrder(BaseModel):
    patient_name: Optional[str] = Field(description="Patient full name as written")
    prescriber_name: Optional[str] = Field(description="Prescriber name, e.g. 'Okafor'")
    drug_name: Optional[str] = Field(description="Active drug, generic or brand name")
    route: Literal["oral", "topical"]
    dose_mg: Optional[float] = Field(description="Oral dose per administration in mg (convert mcg to mg)")
    concentration_pct: Optional[float] = Field(description="Topical strength in percent, if topical")
    frequency_per_day: Optional[int]
    duration_days: Optional[int]
    quantity: Optional[float] = Field(description="Topical quantity in grams, if given")
    notes: Optional[str] = Field(description="Patient needs mentioned: can't swallow, allergies, dietary limits")


def _client():
    import anthropic
    return anthropic.Anthropic()


def _call(**kwargs):
    """messages.parse with the refusal fallback; retry without it if the
    endpoint (e.g. a proxy or cloud platform) rejects the beta parameter."""
    import anthropic
    client = _client()
    try:
        return client.messages.parse(
            extra_headers={"anthropic-beta": FALLBACK_BETA},
            extra_body={"fallbacks": "default"},
            **kwargs,
        )
    except anthropic.BadRequestError:
        return client.messages.parse(**kwargs)


def parse_order(text: str) -> ParsedOrder:
    import anthropic
    try:
        resp = _call(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            system=("You extract prescription details from pharmacy order text. Copy names as written. "
                    "Only fill a field if the text states it; otherwise leave it null."),
            messages=[{"role": "user", "content": text}],
            output_format=ParsedOrder,
        )
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not reach the Claude API: {e}") from e
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not parse this order.")
    return resp.parsed_output


class Brief(BaseModel):
    summary: str = Field(description="2-4 sentence plain-English brief for the pharmacist")
    action_items: list[str] = Field(description="Concrete things the pharmacist should do before approving")


def summarize(order_facts: dict) -> Brief:
    resp = _call(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "medium"},
        system=("You brief a compounding pharmacist on an order prepared by software agents. Use only the facts "
                "given. Do not add clinical claims that are not in the facts. Be direct and short."),
        messages=[{"role": "user", "content": json.dumps(order_facts, default=str)}],
        output_format=Brief,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not summarise this order.")
    return resp.parsed_output
