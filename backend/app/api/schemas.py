from pydantic import BaseModel, Field


class ArxivSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    max_results: int = Field(default=8, ge=1, le=20)


class ArxivIngestRequest(BaseModel):
    arxiv_id: str = Field(min_length=4, max_length=40)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    paper_id: str | None = None


class SourceOut(BaseModel):
    index: int
    paper_id: str
    paper_title: str
    section: str
    page: int
    text: str


class TrustSignalsOut(BaseModel):
    retrieval_margin: float
    rerank_confidence: float
    citation_pass_rate: float
    self_consistency: float
    n_sources: int
    generative: bool


class ChatResponse(BaseModel):
    answer_id: str
    answer: str
    mode: str
    sources: list[SourceOut]
    trust_score: int
    trust_explanation: str
    trust_signals: TrustSignalsOut
    abstained: bool
    latency_ms: int


class FeedbackRequest(BaseModel):
    answer_id: str
    rating: int
    comment: str | None = None


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


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


class PaperOut(BaseModel):
    id: str
    title: str
    authors: str
    year: int | None
    arxiv_id: str | None
    abstract: str
    num_pages: int
    num_chunks: int
    source: str


class JobOut(BaseModel):
    job_id: str
    kind: str
    status: str
    stage: str
    progress: float
    message: str
    error: str | None
    paper_id: str | None
    result: dict = {}
