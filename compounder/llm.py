"""LLM integration (optional): Claude or Gemini.

Used only for language tasks:
  1. parse_order: turn a free-text order into a structured prescription.
  2. summarize: write a short plain-English brief for the pharmacist from the
     facts the agents already put in the graph.
  3. answer_policy: answer a policy question from retrieved excerpts.

Clinical decisions (base choice, dose checks, interactions, coverage) are
never made by the model; they come from graph queries. The app works without
any API key.

Provider choice:
  COMPOUNDER_LLM=claude | gemini   (optional; otherwise Claude if
                                    ANTHROPIC_API_KEY is set, else Gemini if
                                    GEMINI_API_KEY / GOOGLE_API_KEY is set)
  COMPOUNDER_MODEL                 Claude model (default claude-opus-5-5)
  GEMINI_MODEL                     Gemini model (default gemini-flash-latest)
"""
import json
import os
from typing import Literal, Optional

from pydantic import BaseModel, Field

MODEL = os.getenv("COMPOUNDER_MODEL", "claude-opus-5-5")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
# Server-side refusal fallback for Claude: if the model declines, the API
# retries on a fallback model chosen by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _has_claude() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _has_gemini() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def provider() -> Optional[str]:
    """'claude', 'gemini', or None when no key is configured."""
    choice = os.getenv("COMPOUNDER_LLM", "").strip().lower()
    if choice == "claude" and _has_claude():
        return "claude"
    if choice == "gemini" and _has_gemini():
        return "gemini"
    if _has_claude():
        return "claude"
    if _has_gemini():
        return "gemini"
    return None


def provider_label() -> str:
    p = provider()
    return {"claude": f"Claude ({MODEL})", "gemini": f"Gemini ({GEMINI_MODEL})"}.get(p, "not configured")


def available() -> bool:
    return provider() is not None


# --------------------------------------------------------------------------- schemas

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


class Brief(BaseModel):
    summary: str = Field(description="2-4 sentence plain-English brief for the pharmacist")
    action_items: list[str] = Field(description="Concrete things the pharmacist should do before approving")


class PolicyAnswer(BaseModel):
    answer: str = Field(description="Direct answer in plain English, 2-5 sentences")
    cited_sources: list[str] = Field(description="Sources used, copied exactly from the context")


# --------------------------------------------------------------------------- providers

def _claude(system: str, user: str, schema: type[BaseModel], effort: str) -> BaseModel:
    """messages.parse with the refusal fallback; retry without it if the
    endpoint (e.g. a proxy or cloud platform) rejects the beta parameter."""
    import anthropic
    client = anthropic.Anthropic()
    kwargs = dict(model=MODEL, max_tokens=4000, output_config={"effort": effort}, system=system,
                  messages=[{"role": "user", "content": user}], output_format=schema)
    try:
        try:
            resp = client.messages.parse(extra_headers={"anthropic-beta": FALLBACK_BETA},
                                         extra_body={"fallbacks": "default"}, **kwargs)
        except anthropic.BadRequestError:
            resp = client.messages.parse(**kwargs)
    except anthropic.APIConnectionError as e:
        raise RuntimeError(f"Could not reach the Claude API: {e}") from e
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        raise RuntimeError("Claude could not complete this request.")
    return resp.parsed_output


def _gemini(system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        ),
    )
    parsed = resp.parsed
    if isinstance(parsed, schema):
        return parsed
    if parsed is not None:
        return schema.model_validate(parsed)
    if resp.text:  # fall back to validating the raw JSON text
        return schema.model_validate_json(resp.text)
    raise RuntimeError("Gemini returned no usable answer.")


def _structured(system: str, user: str, schema: type[BaseModel], effort: str = "low") -> BaseModel:
    p = provider()
    if p == "claude":
        return _claude(system, user, schema, effort)
    if p == "gemini":
        return _gemini(system, user, schema)
    raise RuntimeError("No LLM configured. Set ANTHROPIC_API_KEY or GEMINI_API_KEY.")


# --------------------------------------------------------------------------- tasks

def parse_order(text: str) -> ParsedOrder:
    return _structured(
        "You extract prescription details from pharmacy order text. Copy names as written. "
        "Only fill a field if the text states it; otherwise leave it null.",
        text, ParsedOrder, "low")


def summarize(order_facts: dict) -> Brief:
    return _structured(
        "You brief a compounding pharmacist on an order prepared by software agents. Use only the facts "
        "given. Do not add clinical claims that are not in the facts. Be direct and short.",
        json.dumps(order_facts, default=str), Brief, "medium")


def answer_policy(question: str, context: dict) -> PolicyAnswer:
    return _structured(
        "You help pharmacists understand regulations and insurance rules. Answer only from the policy "
        "excerpts and formulary facts given. If they do not answer the question, say so.",
        json.dumps({"question": question, **context}, default=str), PolicyAnswer, "low")
