"""Request/response models for the API layer. Kept separate from the SQLModel
table models since the shape we want over the wire isn't always the same as
the shape we store (e.g. we don't want to expose internal ids everywhere)."""

from pydantic import BaseModel


class ArxivSearchRequest(BaseModel):
    query: str
    max_results: int = 10


class ArxivIngestRequest(BaseModel):
    arxiv_id: str


class ChatRequest(BaseModel):
    question: str
    paper_id: str | None = None  # if set, scopes retrieval to a single paper


class SourceOut(BaseModel):
    index: int
    paper_id: str
    paper_title: str
    section: str
    text: str


class ChatResponse(BaseModel):
    answer_id: str
    answer: str
    sources: list[SourceOut]
    trust_score: int
    trust_explanation: str
    abstained: bool


class FeedbackRequest(BaseModel):
    answer_id: str
    rating: int
    comment: str | None = None


class ResearchRequest(BaseModel):
    question: str


class MatrixRowOut(BaseModel):
    paper_title: str
    paper_id: str
    method: str
    dataset: str
    metric_result: str
    limitations: str


class TraceStepOut(BaseModel):
    kind: str
    detail: str


class ResearchResponse(BaseModel):
    narrative: str
    matrix: list[MatrixRowOut]
    trace: list[TraceStepOut]
