"""Training helpers for distilled ChainRight records."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .pretraining import PretrainingRecord
from .uses import UsesCollection


@dataclass
class TrainingRun:
    """Training results for a distilled dataset."""

    records_trained: int
    avg_retrieval_time_ms: float
    avg_generation_time_ms: float
    avg_total_time_ms: float
    avg_relevance_score: float
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)


class TrainingPipeline:
    """Summarize and persist training metadata for distilled records."""

    def __init__(self) -> None:
        self.runs: List[TrainingRun] = []

    def train(self, records: List[PretrainingRecord], uses: Optional[UsesCollection] = None) -> TrainingRun:
        collection = uses or UsesCollection([record.to_use_event() for record in records])
        summary = collection.summary()
        run = TrainingRun(
            records_trained=len(records),
            avg_retrieval_time_ms=summary["avg_retrieval_time_ms"],
            avg_generation_time_ms=summary["avg_generation_time_ms"],
            avg_total_time_ms=summary["avg_total_time_ms"],
            avg_relevance_score=summary["avg_relevance_score"],
            metrics={
                "retrieval_share": (
                    summary["avg_retrieval_time_ms"] / summary["avg_total_time_ms"]
                    if summary["avg_total_time_ms"] else 0.0
                ),
                "generation_share": (
                    summary["avg_generation_time_ms"] / summary["avg_total_time_ms"]
                    if summary["avg_total_time_ms"] else 0.0
                ),
            },
        )
        self.runs.append(run)
        return run

    def export_run(self, path: str | Path, run: Optional[TrainingRun] = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        run = run or (self.runs[-1] if self.runs else None)
        if run is None:
            raise ValueError("No training run available to export")

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(run.__dict__, handle, indent=2)
        return path

