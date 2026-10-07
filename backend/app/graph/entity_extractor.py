"""
Extracts named methods, datasets, metrics, models and tasks from a paper.
Prefers a local gazetteer of well-known ML entities (no LLM, no cost, no
latency) and falls back to an LLM pass when one is configured, to catch
paper-specific names the gazetteer will never have.
"""

import re
from collections import Counter

from app.core.llm import chat_json, llm_available
from app.db.models import EntityType

GAZETTEER: dict[str, EntityType] = {
    # methods
    "self-attention": EntityType.method,
    "multi-head attention": EntityType.method,
    "attention": EntityType.method,
    "transformer": EntityType.method,
    "dropout": EntityType.method,
    "layer normalization": EntityType.method,
    "residual connection": EntityType.method,
    "masked language modeling": EntityType.method,
    "next sentence prediction": EntityType.method,
    "in-context learning": EntityType.method,
    "few-shot": EntityType.method,
    "fine-tuning": EntityType.method,
    "backpropagation": EntityType.method,
    "beam search": EntityType.method,
    "byte-pair encoding": EntityType.method,
    "wordpiece": EntityType.method,
    "reinforcement learning": EntityType.method,
    "contrastive learning": EntityType.method,
    "knowledge distillation": EntityType.method,
    # datasets
    "imagenet": EntityType.dataset,
    "cifar-10": EntityType.dataset,
    "cifar-100": EntityType.dataset,
    "mnist": EntityType.dataset,
    "squad": EntityType.dataset,
    "glue": EntityType.dataset,
    "superglue": EntityType.dataset,
    "wmt 2014": EntityType.dataset,
    "wmt14": EntityType.dataset,
    "penn treebank": EntityType.dataset,
    "wikitext": EntityType.dataset,
    "bookcorpus": EntityType.dataset,
    "common crawl": EntityType.dataset,
    "c4": EntityType.dataset,
    "openwebtext": EntityType.dataset,
    "ms marco": EntityType.dataset,
    "natural questions": EntityType.dataset,
    "hotpotqa": EntityType.dataset,
    "triviaqa": EntityType.dataset,
    "coco": EntityType.dataset,
    # metrics
    "bleu": EntityType.metric,
    "rouge": EntityType.metric,
    "meteor": EntityType.metric,
    "f1": EntityType.metric,
    "exact match": EntityType.metric,
    "perplexity": EntityType.metric,
    "accuracy": EntityType.metric,
    "auc": EntityType.metric,
    "ndcg": EntityType.metric,
    "mrr": EntityType.metric,
    "map": EntityType.metric,
    # models
    "bert": EntityType.model,
    "gpt-2": EntityType.model,
    "gpt-3": EntityType.model,
    "gpt-4": EntityType.model,
    "t5": EntityType.model,
    "roberta": EntityType.model,
    "xlnet": EntityType.model,
    "albert": EntityType.model,
    "resnet": EntityType.model,
    "resnet-50": EntityType.model,
    "lstm": EntityType.model,
    "gru": EntityType.model,
    "elmo": EntityType.model,
    "word2vec": EntityType.model,
    "glove": EntityType.model,
    "llama": EntityType.model,
    # tasks
    "machine translation": EntityType.task,
    "named entity recognition": EntityType.task,
    "question answering": EntityType.task,
    "text classification": EntityType.task,
    "language modeling": EntityType.task,
    "summarization": EntityType.task,
    "sentiment analysis": EntityType.task,
}

# Longest names first so "multi-head attention" wins over "attention".
_SORTED_NAMES = sorted(GAZETTEER, key=len, reverse=True)
_PATTERNS = [(re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE), name) for name in _SORTED_NAMES]


def canonical(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def extract_entities(text: str) -> list[tuple[str, EntityType, int]]:
    haystack = text[:20000]
    counts: Counter[tuple[str, EntityType]] = Counter()
    for pattern, name in _PATTERNS:
        n = len(pattern.findall(haystack))
        if n:
            counts[(name, GAZETTEER[name])] += n

    if llm_available():
        for name, entity_type in _llm_extract(haystack[:3500]):
            key = (name, entity_type)
            counts[key] += max(counts[key], 1)

    return [(name, etype, n) for (name, etype), n in counts.most_common(40)]


_LLM_PROMPT = """Extract named entities from this research paper excerpt.
Only include entities that are explicitly named. Categories: method, dataset, metric, model, task.

Text:
{text}

Return JSON: {{"entities": [{{"name": "...", "type": "method|dataset|metric|model|task"}}]}}"""


def _llm_extract(text: str) -> list[tuple[str, EntityType]]:
    result = chat_json([{"role": "user", "content": _LLM_PROMPT.format(text=text)}])
    found = []
    allowed = {t.value for t in EntityType}
    for item in result.get("entities", []):
        name = (item.get("name") or "").strip()
        type_str = (item.get("type") or "").strip().lower()
        if name and type_str in allowed:
            found.append((name, EntityType(type_str)))
    return found
