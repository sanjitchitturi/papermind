from app.db.models import EntityType
from app.graph.entity_extractor import extract_entities


def test_gazetteer_finds_transformer_and_bleu():
    text = (
        "The Transformer uses self-attention and is evaluated with BLEU on the WMT 2014 English-German task. "
        "BERT uses masked language modeling. GPT-3 demonstrates in-context learning."
    )
    found = {(name, etype) for name, etype, _ in extract_entities(text)}
    assert ("self-attention", EntityType.method) in found
    assert ("bleu", EntityType.metric) in found
    assert ("wmt 2014", EntityType.dataset) in found
    assert ("bert", EntityType.model) in found
    assert ("gpt-3", EntityType.model) in found


def test_longest_match_wins_over_substring():
    text = "We use multi-head attention rather than a single attention head."
    names = [name for name, etype, _ in extract_entities(text) if etype.value == "method"]
    assert "multi-head attention" in names
