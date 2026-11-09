from app.core.llm import LLMProviderError
from app.generation import answer_generator, citation_verifier
from app.generation.answer_generator import GeneratedAnswer, Source
from app.retrieval.passages import Passage
from app.trust import trust_score


def fail(*args, **kwargs):
    raise LLMProviderError("Provider rejected credentials")


def test_generation_reverts_to_quotes_on_bad_key(monkeypatch):
    monkeypatch.setattr(answer_generator, "llm_available", lambda: True)
    monkeypatch.setattr(answer_generator, "chat", fail)
    passage = Passage("c", "p", "Paper", "", "intro", 1, "Attention uses evidence", 0.5)
    generated = answer_generator.generate_answer("attention?", [passage])
    assert generated.mode == "extractive"
    assert "Attention uses evidence" in generated.answer


def test_unverified_citations_never_count_as_supported(monkeypatch):
    monkeypatch.setattr(citation_verifier, "llm_available", lambda: True)
    monkeypatch.setattr(citation_verifier, "chat_json", fail)
    generated = GeneratedAnswer("Claim [1].", [], "generative")
    assert citation_verifier.verify_citations(generated) == []
    assert citation_verifier.pass_rate([]) == 0
    monkeypatch.setattr(citation_verifier, "chat_json", lambda *args: {"checks": [None, "bad"]})
    assert citation_verifier.pass_rate(citation_verifier.verify_citations(generated)) == 0


def test_optional_self_consistency_failure_does_not_break_answer(monkeypatch):
    monkeypatch.setattr(trust_score, "llm_available", lambda: True)
    monkeypatch.setattr(trust_score.get_settings(), "trust_self_consistency", True)
    monkeypatch.setattr(trust_score, "chat", fail)
    assert trust_score.compute_self_consistency("question", [], "answer") == 0


def test_missing_citation_check_counts_as_unsupported(monkeypatch):
    monkeypatch.setattr(citation_verifier, "llm_available", lambda: True)
    answer = "First claim [1]. Second claim [2]."
    sources = [Source(i, f"c{i}", "p", "Paper", "intro", 1, "evidence") for i in (1, 2)]
    monkeypatch.setattr(citation_verifier, "chat_json", lambda *args: {
        "checks": [{"sentence": "First claim [1].", "source": 1, "verdict": "supported"}]
    })
    checks = citation_verifier.verify_citations(GeneratedAnswer(answer, sources, "generative"))
    assert len(checks) == 2
    assert citation_verifier.pass_rate(checks) == 0.5
    assert checks[1].verdict == "unsupported"


def test_uncited_generated_sentence_counts_as_unsupported(monkeypatch):
    monkeypatch.setattr(citation_verifier, "llm_available", lambda: True)
    monkeypatch.setattr(citation_verifier, "chat_json", lambda *args: {
        "checks": [{"sentence": "Cited claim [1].", "source": 1, "verdict": "supported"}]
    })
    source = Source(1, "c1", "p", "Paper", "intro", 1, "evidence")
    answer = GeneratedAnswer("Cited claim [1]. Another unsupported assertion.", [source], "generative")
    checks = citation_verifier.verify_citations(answer)
    assert citation_verifier.pass_rate(checks) == 0.5
    assert checks[1].source_index == 0
