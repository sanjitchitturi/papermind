"""
Extracts structured entities (methods, datasets, metrics, models) from a
paper's abstract and section text using the LLM's function-calling-style
JSON output. This is what the knowledge graph is built from.
"""

from app.core.llm import chat_json
from app.db.models import EntityType

EXTRACTION_PROMPT = """Read the following text from a research paper and extract the
key entities it mentions. Only include entities that are explicitly named, don't infer
ones that aren't actually in the text.

Categories:
- method: named techniques or algorithms (e.g. "self-attention", "dropout")
- dataset: named datasets (e.g. "ImageNet", "GLUE")
- metric: named evaluation metrics (e.g. "BLEU", "F1 score")
- model: named models or architectures (e.g. "BERT", "ResNet-50")

Text:
{text}

Return JSON: {{"entities": [{{"name": "...", "type": "method|dataset|metric|model"}}]}}"""


def extract_entities(text: str) -> list[tuple[str, EntityType]]:
    result = chat_json([{"role": "user", "content": EXTRACTION_PROMPT.format(text=text[:4000])}])
    entities = []
    for item in result.get("entities", []):
        name = (item.get("name") or "").strip()
        type_str = (item.get("type") or "").strip().lower()
        if not name or type_str not in {t.value for t in EntityType}:
            continue
        entities.append((name, EntityType(type_str)))
    return entities
