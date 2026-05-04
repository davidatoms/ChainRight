"""Single use event objects for retrieval and generation benchmarking."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class UseEvent:
    """Represents one retrieval-then-generation interaction."""

    user_id: str
    input_text: str
    retrieved_items: List[Dict[str, Any]] = field(default_factory=list)
    generated_text: str = ""
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    relevance_score: float = 0.0
    output_kind: str = "generation"
    source_id: Optional[str] = None
    wallet_address: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_id: str = field(default_factory=lambda: f"use_{uuid.uuid4().hex[:12]}")

    @property
    def total_time_ms(self) -> float:
        return self.retrieval_time_ms + self.generation_time_ms

    @property
    def retrieval_ratio(self) -> float:
        total = self.total_time_ms
        return self.retrieval_time_ms / total if total else 0.0

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_time_ms"] = self.total_time_ms
        data["retrieval_ratio"] = self.retrieval_ratio
        return data

