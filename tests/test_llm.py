"""LLM provider selection and Gemini response handling (no network, no keys)."""
import sys
import types

from compounder import llm

KEYS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GEMINI_API_KEY", "GOOGLE_API_KEY", "COMPOUNDER_LLM")


def _env(monkeypatch, **kv):
    for k in KEYS:
        monkeypatch.delenv(k, raising=False)
    for k, v in kv.items():
        monkeypatch.setenv(k, v)


def test_provider_selection(monkeypatch):
    _env(monkeypatch)
    assert llm.provider() is None and not llm.available()
    _env(monkeypatch, GEMINI_API_KEY="g")
    assert llm.provider() == "gemini"
    _env(monkeypatch, ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g")
    assert llm.provider() == "claude"
    _env(monkeypatch, ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", COMPOUNDER_LLM="gemini")
    assert llm.provider() == "gemini"


def test_gemini_parse_order_with_stub(monkeypatch):
    _env(monkeypatch, GEMINI_API_KEY="g")
    captured = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured.update(model=model, schema=config.response_schema, mime=config.response_mime_type)
            return types.SimpleNamespace(parsed=None, text='{"patient_name": "Maya Chen", "prescriber_name": "Okafor", '
                                         '"drug_name": "amlodipine", "route": "oral", "dose_mg": 1.5, '
                                         '"concentration_pct": null, "frequency_per_day": 1, "duration_days": 30, '
                                         '"quantity": null, "notes": "no dyes"}')

    class FakeClient:
        def __init__(self, api_key):
            captured["key"] = api_key
            self.models = FakeModels()

    import google.genai as genai
    monkeypatch.setattr(genai, "Client", FakeClient)
    out = llm.parse_order("Maya Chen, amlodipine 1.5 mg daily")
    assert out.drug_name == "amlodipine" and out.dose_mg == 1.5
    assert captured["schema"] is llm.ParsedOrder and captured["mime"] == "application/json" and captured["key"] == "g"
